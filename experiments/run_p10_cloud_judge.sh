#!/usr/bin/env bash
set -euo pipefail

# Run official-style p10 LLM-as-Judge evaluation.
#
# Before running, configure an OpenAI-compatible judge endpoint, for example:
#   export LLM_BASE_URL="https://api.deepseek.com/v1"
#   export LLM_API_KEY="sk-..."
#   export LLM_MODEL="deepseek-v4-flash"
#
# Or DashScope:
#   export LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
#   export LLM_API_KEY="sk-..."
#   export LLM_MODEL="qwen-plus"

if [[ -z "${LLM_BASE_URL:-}" || -z "${LLM_API_KEY:-}" || -z "${LLM_MODEL:-}" ]]; then
  echo "Please set LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL for the judge endpoint." >&2
  exit 1
fi

RESULT_DIR="experiments/results"

python eval_kit/run_judge.py \
  --predictions "$RESULT_DIR/predictions_nomem_p10.json" \
  --output "$RESULT_DIR/results_nomem_p10.json" \
  --num_workers 4

python eval_kit/run_judge.py \
  --predictions "$RESULT_DIR/predictions_fullctx_p10.json" \
  --output "$RESULT_DIR/results_fullctx_p10.json" \
  --num_workers 4

python eval_kit/run_judge.py \
  --predictions "$RESULT_DIR/predictions_rag_p10.json" \
  --output "$RESULT_DIR/results_rag_p10.json" \
  --num_workers 4

python eval_kit/run_judge.py \
  --predictions "$RESULT_DIR/predictions_update_reflection_p10.json" \
  --output "$RESULT_DIR/results_update_reflection_p10.json" \
  --num_workers 4

python experiments/analyze_bad_cases.py \
  --results "$RESULT_DIR/results_update_reflection_p10.json" \
  --output "$RESULT_DIR/bad_cases_update_reflection_p10.json" \
  --limit 10

