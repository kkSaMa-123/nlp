#!/usr/bin/env bash
set -euo pipefail

# Run from the project root:
#   bash experiments/run_small_experiments.sh
#
# The script assumes Ollama is running and env.local-ollama.sh has the model
# endpoint for qwen2.5:3b.

source env.local-ollama.sh

export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"

EVAL_SET="eval_kit/eval_set_small.json"
RESULT_DIR="experiments/results"

python eval_kit/run_generation.py \
  --eval_set "$EVAL_SET" \
  --agent memory_agent.agent.baselines:NoMemoryAgent \
  --output "$RESULT_DIR/predictions_nomem_small.json"

python eval_kit/run_generation.py \
  --eval_set "$EVAL_SET" \
  --agent eval_kit.agent_template:FullContextAgent \
  --output "$RESULT_DIR/predictions_fullctx_small.json"

python eval_kit/run_generation.py \
  --eval_set "$EVAL_SET" \
  --agent memory_agent.agent.baselines:RawTurnRAGAgent \
  --output "$RESULT_DIR/predictions_rag_small.json"

MEMORY_PER_SESSION=4 \
MEMORY_TOP_K=10 \
MEMORY_DETAIL_NOTES=1 \
MEMORY_DETAIL_NOTES_PER_SESSION=3 \
python eval_kit/run_generation.py \
  --eval_set "$EVAL_SET" \
  --agent memory_agent.agent.controller:AppendOnlyMemoryAgent \
  --output "$RESULT_DIR/predictions_append_small_detail.json"

MEMORY_PER_SESSION=4 \
MEMORY_TOP_K=10 \
MEMORY_DETAIL_NOTES=1 \
MEMORY_DETAIL_NOTES_PER_SESSION=3 \
MEMORY_UPDATE_USE_LLM=0 \
python eval_kit/run_generation.py \
  --eval_set "$EVAL_SET" \
  --agent memory_agent.agent.controller:UpdateMemoryAgent \
  --output "$RESULT_DIR/predictions_update_small_rule.json"

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
  --output "$RESULT_DIR/predictions_update_reflection_small.json"

