# Long-Term Memory Agent

This repository contains the course project implementation for a long-term
memory dialogue agent. The current runnable baseline is a no-memory agent.

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
