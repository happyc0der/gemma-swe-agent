#!/bin/bash
# Unattended: once the Ollama holdout batch is done and the 12B weights are complete, free the GPU, start vLLM,
# smoke-test it, and run the holdout with the day-2 submission config (thinking on, real thinking_budget).
export DOCKER_CONFIG=$HOME/.docker-ssh; export PATH="$HOME/.local/bin:$PATH"
R=~/Projects/gemma-swe-agent; LOG=$R/serve/after_batch.log; exec >> $LOG 2>&1
echo "[$(date)] waiting for holdout batch + weights"
until grep -q BATCH_DONE $R/harness/results/msi-v3-nothink-holdout.console 2>/dev/null; do sleep 60; done
until [ -f ~/models/gemma-4-12B-it-qat-w4a16-ct/model.safetensors ] && [ "$(stat -c %s ~/models/gemma-4-12B-it-qat-w4a16-ct/model.safetensors)" -ge 10264000000 ]; do sleep 60; done
echo "[$(date)] batch done, weights complete; syncing repo"
cd $R && git pull -q || echo "git pull failed (continuing)"
OL=/mnt/c/Users/KESHAV/AppData/Local/Programs/Ollama/ollama.exe
OLLAMA_HOST=127.0.0.1:11435 $OL stop gemma4:12b-32k 2>/dev/null; sleep 5
echo "[$(date)] starting vLLM"
cd $R/serve && nohup bash vllm_serve.sh >/dev/null 2>&1 &
for i in $(seq 1 60); do sleep 15; curl -s --max-time 5 http://127.0.0.1:8000/v1/models | grep -q gemma && break; done
if ! curl -s --max-time 5 http://127.0.0.1:8000/v1/models | grep -q gemma; then echo "[$(date)] vLLM did not come up; log tail:"; tail -30 vllm_serve.log; exit 1; fi
echo "[$(date)] vLLM up; smoke test"
curl -s http://127.0.0.1:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"gemma-4-12b-it-qat-w4a16-ct","messages":[{"role":"user","content":"Read src/app.py lines 1 to 20."}],"tools":[{"type":"function","function":{"name":"read_file","parameters":{"type":"object","properties":{"filepath":{"type":"string"},"start_line":{"type":"integer"},"end_line":{"type":"integer"}},"required":["filepath"]}}}],"max_tokens":300}' | head -c 600; echo
echo "[$(date)] holdout batch with day-2 config on vLLM"
API_BASE=http://127.0.0.1:8000/v1 SERVED_MODEL=gemma-4-12b-it-qat-w4a16-ct bash $R/serve/holdout_batch.sh ../../submission msi-day2cfg-vllm 10 50
echo "[$(date)] AFTER_BATCH_DONE"
