"""Convenience evaluation entry point for this project.

This wraps the provided eval_kit scripts and keeps the project-level command
shorter. It runs generation, prints quick local metrics, and can optionally run
LLM-as-Judge when a judge endpoint is configured.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval_set", required=True)
    parser.add_argument(
        "--agent",
        default="memory_agent.agent.controller:UpdateReflectionAgent",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--judge_output", default=None)
    parser.add_argument("--judge", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--num_workers", type=int, default=4)
    args = parser.parse_args()

    generation_cmd = [
        sys.executable,
        "eval_kit/run_generation.py",
        "--eval_set",
        args.eval_set,
        "--agent",
        args.agent,
        "--output",
        args.output,
    ]
    if args.resume:
        generation_cmd.append("--resume")
    run(generation_cmd)

    run([sys.executable, "experiments/summarize_predictions.py", args.output])

    if args.judge:
        judge_output = args.judge_output
        if not judge_output:
            out = Path(args.output)
            judge_output = str(out.with_name(out.stem.replace("predictions", "results") + ".json"))
        run(
            [
                sys.executable,
                "eval_kit/run_judge.py",
                "--predictions",
                args.output,
                "--output",
                judge_output,
                "--num_workers",
                str(args.num_workers),
            ]
        )


if __name__ == "__main__":
    main()

