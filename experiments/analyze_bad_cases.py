"""Extract bad cases from judged result files for manual analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True, help="results_*.json from run_judge.py")
    parser.add_argument("--output", required=True, help="bad-case output JSON")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    results = json.loads(Path(args.results).read_text())
    graded = results.get("graded", [])
    bad = [
        {
            "qa_id": item.get("qa_id"),
            "category_name": item.get("category_name"),
            "question": item.get("question"),
            "reference": item.get("reference"),
            "prediction": item.get("prediction"),
            "judge_label": item.get("judge_label"),
            "judge_reasoning": item.get("judge_reasoning"),
            "f1": item.get("f1"),
            "likely_error_stage": "to_analyze",
            "notes": "",
        }
        for item in graded
        if item.get("judge_label") == "WRONG"
    ]
    bad = sorted(bad, key=lambda item: (item.get("f1") or 0.0, item.get("qa_id") or ""))
    Path(args.output).write_text(
        json.dumps(bad[: args.limit], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"saved {min(len(bad), args.limit)} bad cases -> {args.output}")


if __name__ == "__main__":
    main()

