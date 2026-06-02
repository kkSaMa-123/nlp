"""Create evidence-backed bad case analysis from judge results and agent logs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str):
    return json.loads(Path(path).read_text())


def load_answer_logs(log_paths: list[str]) -> dict[str, dict]:
    by_question = {}
    for path in log_paths:
        with open(path, encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                if item.get("event") == "answer":
                    by_question[item.get("question", "")] = {
                        "log_file": path,
                        "answer": item.get("answer", ""),
                        "retrieved": item.get("retrieved", []),
                    }
    return by_question


def guess_error_stage(prediction: str, retrieved: list[dict]) -> str:
    pred = str(prediction).strip().lower()
    if pred in {"unknown", "unknown."}:
        if not retrieved:
            return "检索失败：没有检索到可用记忆"
        return "写入或检索失败：模型回答 unknown，需检查 top memories 是否含答案"
    if retrieved:
        return "生成失败或证据不足：有检索结果，但答案与参考不一致"
    return "检索失败：未找到记忆但模型仍生成了答案"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--logs", nargs="+", required=True)
    parser.add_argument("--output_json", required=True)
    parser.add_argument("--output_md", required=True)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    results = load_json(args.results)
    answer_logs = load_answer_logs(args.logs)
    wrong = [
        item
        for item in results.get("graded", [])
        if item.get("judge_label") == "WRONG"
    ]
    wrong = sorted(wrong, key=lambda item: (item.get("f1") or 0.0, item.get("qa_id") or ""))

    cases = []
    for item in wrong[: args.limit]:
        log = answer_logs.get(item.get("question", ""), {})
        retrieved = log.get("retrieved", [])[:5]
        cases.append(
            {
                "qa_id": item.get("qa_id"),
                "category_name": item.get("category_name"),
                "question": item.get("question"),
                "reference": item.get("reference"),
                "prediction": item.get("prediction"),
                "judge_label": item.get("judge_label"),
                "judge_reasoning": item.get("judge_reasoning"),
                "f1": item.get("f1"),
                "likely_error_stage": guess_error_stage(item.get("prediction", ""), retrieved),
                "log_file": log.get("log_file"),
                "top_retrieved_memories": [
                    {
                        "score": memory.get("score"),
                        "type": memory.get("type"),
                        "date_time": memory.get("date_time"),
                        "text": memory.get("text"),
                    }
                    for memory in retrieved
                ],
            }
        )

    Path(args.output_json).write_text(json.dumps(cases, ensure_ascii=False, indent=2))
    Path(args.output_md).write_text(render_markdown(cases), encoding="utf-8")
    print(f"saved {len(cases)} cases -> {args.output_json}, {args.output_md}")


def render_markdown(cases: list[dict]) -> str:
    lines = ["# p10 Bad Case 分析", ""]
    for i, case in enumerate(cases, start=1):
        lines.extend(
            [
                f"## Case {i}: `{case['qa_id']}`",
                "",
                f"- 类型：{case['category_name']}",
                f"- 问题：{case['question']}",
                f"- 参考答案：{case['reference']}",
                f"- 模型回答：{case['prediction']}",
                f"- Judge 标签：{case['judge_label']}",
                f"- Judge 理由：{case['judge_reasoning']}",
                f"- 初步错误定位：{case['likely_error_stage']}",
                "",
                "Top retrieved memories:",
                "",
            ]
        )
        for memory in case["top_retrieved_memories"]:
            lines.append(
                f"- score={memory.get('score'):.3f} | type={memory.get('type')} | "
                f"{memory.get('date_time')} | {memory.get('text')}"
            )
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()

