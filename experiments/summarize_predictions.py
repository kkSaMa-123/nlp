"""Print quick local metrics for prediction JSON files.

These metrics are only for development. Final reporting should use
eval_kit/run_judge.py for LLM-as-Judge scores.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


def normalize(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def f1_score(prediction: str, reference: str) -> float:
    pred_tokens = normalize(prediction).split()
    ref_tokens = normalize(reference).split()
    if not pred_tokens or not ref_tokens:
        return float(pred_tokens == ref_tokens)

    counts: dict[str, int] = {}
    for token in pred_tokens:
        counts[token] = counts.get(token, 0) + 1

    common = 0
    for token in ref_tokens:
        if counts.get(token, 0) > 0:
            common += 1
            counts[token] -= 1

    if common == 0:
        return 0.0
    precision = common / len(pred_tokens)
    recall = common / len(ref_tokens)
    return 2 * precision * recall / (precision + recall)


def exact_match(prediction: str, reference: str) -> float:
    return float(normalize(prediction) == normalize(reference))


def summarize(path: Path) -> dict:
    data = json.loads(path.read_text())
    by_category: dict[str, list[float]] = defaultdict(list)
    f1_values = []
    em_values = []
    unknown = 0
    errors = 0
    latency = 0.0

    for item in data:
        pred = item.get("prediction", "")
        ref = item.get("reference", "")
        f1 = f1_score(pred, ref)
        em = exact_match(pred, ref)
        f1_values.append(f1)
        em_values.append(em)
        by_category[item.get("category_name", "unknown")].append(f1)
        if str(pred).strip().lower() in {"unknown", "unknown."}:
            unknown += 1
        if item.get("error"):
            errors += 1
        latency += float(item.get("latency_sec", 0.0))

    n = len(data) or 1
    return {
        "file": str(path),
        "n": len(data),
        "f1": round(sum(f1_values) / n, 3),
        "em": round(sum(em_values) / n, 3),
        "unknown": unknown,
        "errors": errors,
        "avg_latency": round(latency / n, 3),
        "by_category": {
            name: round(sum(values) / len(values), 3)
            for name, values in sorted(by_category.items())
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", nargs="+", help="Prediction JSON files")
    args = parser.parse_args()

    for filename in args.predictions:
        result = summarize(Path(filename))
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

