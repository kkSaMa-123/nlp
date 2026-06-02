#!/usr/bin/env bash
set -euo pipefail

# Run from the project root:
#   bash experiments/run_p10_experiments.sh
#
# This script runs the p10 generation experiments used in the progress summary.
# It assumes Ollama is running and qwen2.5:3b is available.

source env.local-ollama.sh

export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"

EVAL_SET="eval_kit/eval_set_p10.json"
RESULT_DIR="experiments/results"

if [ ! -f "$EVAL_SET" ]; then
  python eval_kit/prepare_eval_set.py \
    --output "$EVAL_SET" \
    --per_category 10 \
    --seed 42
fi

python eval_kit/run_generation.py \
  --eval_set "$EVAL_SET" \
  --agent memory_agent.agent.baselines:NoMemoryAgent \
  --output "$RESULT_DIR/predictions_nomem_p10.json" \
  --resume

python eval_kit/run_generation.py \
  --eval_set "$EVAL_SET" \
  --agent eval_kit.agent_template:FullContextAgent \
  --output "$RESULT_DIR/predictions_fullctx_p10.json" \
  --resume

python eval_kit/run_generation.py \
  --eval_set "$EVAL_SET" \
  --agent memory_agent.agent.baselines:RawTurnRAGAgent \
  --output "$RESULT_DIR/predictions_rag_p10.json" \
  --resume

MEMORY_PER_SESSION=4 \
MEMORY_TOP_K=10 \
MEMORY_DETAIL_NOTES=1 \
MEMORY_DETAIL_NOTES_PER_SESSION=3 \
MEMORY_UPDATE_USE_LLM=0 \
MEMORY_REFLECTIONS=6 \
MEMORY_REFLECTION_INPUTS=120 \
python eval_kit/run_generation.py \
  --eval_set "$EVAL_SET" \
  --agent memory_agent.agent.controller:UpdateReflectionAgent \
  --output "$RESULT_DIR/predictions_update_reflection_p10.json" \
  --resume

python experiments/summarize_predictions.py \
  "$RESULT_DIR/predictions_nomem_p10.json" \
  "$RESULT_DIR/predictions_fullctx_p10.json" \
  "$RESULT_DIR/predictions_rag_p10.json" \
  "$RESULT_DIR/predictions_update_reflection_p10.json"

python experiments/compute_costs.py \
  --eval_set "$EVAL_SET" \
  --output "$RESULT_DIR/cost_summary_p10.json" \
  --prediction no_memory "$RESULT_DIR/predictions_nomem_p10.json" \
  --prediction full_context "$RESULT_DIR/predictions_fullctx_p10.json" \
  --prediction raw_turn_rag "$RESULT_DIR/predictions_rag_p10.json" \
  --prediction update_reflection "$RESULT_DIR/predictions_update_reflection_p10.json"
