#!/bin/bash
# vLLM proxy on the MSI (RTX 3080 Ti 16 GB): Gemma 4 12B W4A16 with the competition's parsers.
# Memory-fitted: no LoRA buffers, 2 concurrent sequences, text-only (vision tower off), eager mode (no nvcc in WSL).
# Launch via: schtasks /run /tn swe_vllm_serve
cd ~/Projects/gemma-swe-agent/serve
MODEL_DIR=${MODEL_DIR:-$HOME/models/gemma-4-12B-it-qat-w4a16-ct}
exec .venv/bin/python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_DIR" --served-model-name gemma-4-12b-it-qat-w4a16-ct \
  --host 0.0.0.0 --port 8000 \
  --max-model-len 32768 --max-num-seqs 2 --gpu-memory-utilization 0.95 \
  --limit-mm-per-prompt '{"image":0,"audio":0}' \
  --tool-call-parser gemma4 --enable-auto-tool-choice --reasoning-parser gemma4 \
  --enforce-eager \
  > vllm_serve.log 2>&1
