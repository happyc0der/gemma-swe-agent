#!/bin/bash
# vLLM proxy on the MSI: Gemma 4 12B W4A16 with the same parsers/limits as the competition harness (README section 3.3).
# Launch via: schtasks /run /tn swe_vllm_serve
cd ~/Projects/gemma-swe-agent/serve
MODEL_DIR=${MODEL_DIR:-$HOME/models/gemma-4-12B-it-qat-w4a16-ct}
exec .venv/bin/python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_DIR" --served-model-name gemma-4-12b-it-qat-w4a16-ct \
  --host 0.0.0.0 --port 8000 \
  --max-model-len 32768 --gpu-memory-utilization 0.90 \
  --tool-call-parser gemma4 --enable-auto-tool-choice --reasoning-parser gemma4 \
  --enable-lora --max-loras 8 --max-lora-rank 128 \
  > vllm_serve.log 2>&1
