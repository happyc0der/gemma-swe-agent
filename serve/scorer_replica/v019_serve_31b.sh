#!/bin/bash
# Scorer replica: wheelhouse vLLM 0.19.1 serving the REAL 31B W4A16 on the 16 GB 3080 Ti (port 8001).
# Speed knobs (env): OFFLOAD_GB (weights kept in RAM), KV_DTYPE (auto = scorer-faithful bf16, fp8 = half the KV),
#   PIN (1 = pinned + zero-copy UVA under WSL via local patch), EAGER (1 = no CUDA graphs), MAX_LEN, MNBT.
export VLLM_WORKER_MULTIPROC_METHOD=spawn VLLM_NO_USAGE_STATS=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export VLLM_WSL_PIN=${PIN:-1}
# torch.compile (CUDA graphs) needs an nvcc on PATH; the wheelhouse has none, so borrow the 0.30 venv's pip CUDA toolkit.
export CUDA_HOME=${CUDA_HOME:-$HOME/Projects/gemma-swe-agent/serve/.venv/lib/python3.12/site-packages/nvidia/cu13}
export PATH=$CUDA_HOME/bin:$PATH
EAGER_FLAG=""; [ "${EAGER:-0}" = "1" ] && EAGER_FLAG="--enforce-eager"
# OFFLOAD_BACKEND=prefetch: offload GROUP_N of every GROUP layers and copy them ahead asynchronously (full pinned
# memcpy rate, overlapped with compute); OFFLOAD_BACKEND=uva: zero-copy offload of OFFLOAD_GB (older default).
if [ "${OFFLOAD_BACKEND:-prefetch}" = "prefetch" ]; then
  OFFLOAD_FLAGS="--offload-backend prefetch --offload-group-size ${GROUP:-5} --offload-num-in-group ${GROUP_N:-3} --offload-prefetch-step ${PREFETCH:-2}"
else
  OFFLOAD_FLAGS="--offload-backend uva --cpu-offload-gb ${OFFLOAD_GB:-10.5}"
fi
cd ~ && exec ~/v019/bin/python -m vllm.entrypoints.openai.api_server \
  --model ~/models/gemma-4-31B-it-qat-w4a16-ct --served-model-name gemma-4-31b-it-qat-w4a16-ct \
  --host 127.0.0.1 --port 8001 --tool-call-parser gemma4 --reasoning-parser gemma4 --enable-auto-tool-choice \
  --default-chat-template-kwargs '{"enable_thinking": true}' --max-model-len ${MAX_LEN:-32768} --dtype bfloat16 \
  --language-model-only --kv-cache-dtype ${KV_DTYPE:-auto} \
  --gpu-memory-utilization ${UTIL:-0.92} $OFFLOAD_FLAGS \
  --max-num-seqs 1 --max-num-batched-tokens ${MNBT:-2048} $EAGER_FLAG \
  > ~/v019_serve_31b.log 2>&1
