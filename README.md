# Long-Term Memory Agent

This repository contains the course project implementation for a long-term
memory dialogue agent. It includes baseline agents, an append-only memory
agent, an update/merge memory agent, and an update + reflection agent.

## Environment

Create an isolated conda environment:

```bash
mamba env create -f environment.yml
conda activate memory-agent
```

If the environment already exists, update it with:

```bash
mamba env update -f environment.yml --prune
conda activate memory-agent
```

## Prepare a Small Eval Set

Start with a small sample before running the full evaluation:

```bash
cd eval_kit
python prepare_eval_set.py --output eval_set_small.json --per_category 2 --seed 42
cd ..
```

## Run the No-Memory Baseline

The no-memory baseline answers only from the question itself and is intended as
the required control group.

First configure an OpenAI-compatible chat endpoint. For a local vLLM server, the
defaults in `eval_kit/llm_client.py` are enough:

```bash
export LLM_BASE_URL="http://localhost:8000/v1"
export LLM_API_KEY="EMPTY"
export LLM_MODEL="Qwen/Qwen2.5-3B-Instruct-AWQ"
```

On macOS, the simplest local setup is Ollama:

```bash
brew services start ollama
ollama pull qwen2.5:3b
source env.local-ollama.sh
```

Then run generation:

```bash
python eval_kit/run_generation.py \
  --eval_set eval_kit/eval_set_small.json \
  --agent memory_agent.agent.baselines:NoMemoryAgent \
  --output experiments/results/predictions_nomem_small.json
```

If you do not want to activate the environment in the current shell, use:

```bash
conda run -n memory-agent python eval_kit/run_generation.py \
  --eval_set eval_kit/eval_set_small.json \
  --agent memory_agent.agent.baselines:NoMemoryAgent \
  --output experiments/results/predictions_nomem_small.json
```

For cloud APIs, set `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` to the
provider's OpenAI-compatible endpoint before running the same command.

## Run the Main Memory Agent

The final experimental agent is:

```text
memory_agent.agent.controller:UpdateReflectionAgent
```

It uses extracted memories, high-signal detail notes, rule-based memory
deduplication/merge, and reflection memories.

For a quick small-set run:

```bash
MEMORY_PER_SESSION=4 \
MEMORY_TOP_K=10 \
MEMORY_DETAIL_NOTES=1 \
MEMORY_DETAIL_NOTES_PER_SESSION=3 \
MEMORY_UPDATE_USE_LLM=0 \
MEMORY_REFLECTIONS=6 \
MEMORY_REFLECTION_INPUTS=120 \
MEMORY_ALLOW_INFERENCE=0 \
python eval_kit/run_generation.py \
  --eval_set eval_kit/eval_set_small.json \
  --agent memory_agent.agent.controller:UpdateReflectionAgent \
  --output experiments/results/predictions_update_reflection_small.json \
  --resume
```

`MEMORY_ALLOW_INFERENCE=1` is an optional prompt ablation that lets the model
make cautious "likely/probably" inferences from indirect memories. Current
small-set results show fewer `unknown` answers but slightly lower rough F1, so
the main reported p10 configuration keeps it disabled.

For the p10 experiment used in the current result summary:

```bash
bash experiments/run_p10_experiments.sh
```

The generated p10 files include:

```text
experiments/results/predictions_nomem_p10.json
experiments/results/predictions_fullctx_p10.json
experiments/results/predictions_rag_p10.json
experiments/results/predictions_update_reflection_p10.json
```

## Judge Evaluation

Local judge results with `qwen2.5:3b` are included as development references.
For official-style judging, configure a stronger OpenAI-compatible endpoint
such as DeepSeek or DashScope:

```bash
export LLM_BASE_URL="https://api.deepseek.com/v1"
export LLM_API_KEY="sk-..."
export LLM_MODEL="deepseek-v4-flash"

bash experiments/run_p10_cloud_judge.sh
```

## Result Summary

The current experiment record is:

```text
experiments/results/small_experiment_summary.md
```

The machine-readable result manifest is:

```text
experiments/results/experiment_manifest.json
```
