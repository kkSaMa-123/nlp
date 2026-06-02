"""Estimate LLM call costs and latency from evaluation artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str):
    return json.loads(Path(path).read_text())


def count_eval(eval_set: list[dict]) -> tuple[int, int, int]:
    conversations = len(eval_set)
    sessions = sum(len(item["conversation"].get("sessions", [])) for item in eval_set)
    questions = sum(len(item.get("qa_list", [])) for item in eval_set)
    return conversations, sessions, questions


def summarize_predictions(path: str) -> dict:
    predictions = load_json(path)
    n = len(predictions)
    avg_answer_latency = (
        sum(float(item.get("latency_sec", 0.0)) for item in predictions) / n
        if n
        else 0.0
    )
    return {
        "prediction_file": path,
        "num_predictions": n,
        "errors": sum(1 for item in predictions if item.get("error")),
        "avg_answer_latency_sec": round(avg_answer_latency, 3),
    }


def estimate_calls(
    system: str,
    eval_set: list[dict],
    predictions_path: str,
) -> dict:
    conversations, sessions, questions = count_eval(eval_set)
    pred_summary = summarize_predictions(predictions_path)

    if system in {"no_memory", "full_context", "raw_turn_rag"}:
        ingest_llm_calls = 0
        reflection_llm_calls = 0
        answer_llm_calls = questions
        updater_llm_calls = 0
    elif system == "append_memory":
        ingest_llm_calls = sessions
        reflection_llm_calls = 0
        answer_llm_calls = questions
        updater_llm_calls = 0
    elif system == "update_reflection":
        ingest_llm_calls = sessions
        reflection_llm_calls = conversations
        answer_llm_calls = questions
        updater_llm_calls = 0
    else:
        raise ValueError(f"unknown system: {system}")

    total_llm_calls = (
        ingest_llm_calls + reflection_llm_calls + answer_llm_calls + updater_llm_calls
    )
    return {
        "system": system,
        **pred_summary,
        "num_conversations": conversations,
        "num_sessions": sessions,
        "num_questions": questions,
        "ingest_llm_calls": ingest_llm_calls,
        "reflection_llm_calls": reflection_llm_calls,
        "answer_llm_calls": answer_llm_calls,
        "updater_llm_calls": updater_llm_calls,
        "total_llm_calls": total_llm_calls,
        "avg_llm_calls_per_question": round(total_llm_calls / questions, 3)
        if questions
        else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval_set", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--prediction",
        action="append",
        nargs=2,
        metavar=("SYSTEM", "PATH"),
        required=True,
        help="SYSTEM is one of no_memory, full_context, raw_turn_rag, append_memory, update_reflection",
    )
    args = parser.parse_args()

    eval_set = load_json(args.eval_set)
    rows = [estimate_calls(system, eval_set, path) for system, path in args.prediction]
    Path(args.output).write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"saved cost summary -> {args.output}")
    for row in rows:
        print(
            row["system"],
            "calls/q=",
            row["avg_llm_calls_per_question"],
            "latency=",
            row["avg_answer_latency_sec"],
            "errors=",
            row["errors"],
        )


if __name__ == "__main__":
    main()
