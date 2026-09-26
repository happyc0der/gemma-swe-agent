#!/bin/bash
# One optimisation trial: start the server with the given env, wait, benchmark, record, stop. Usage: TAG=x [env...] bash ~/v019_trial.sh
pkill -f "vllm.entrypoints.openai.api_server"; sleep 8
bash ~/v019_serve_31b.sh & SERVER=$!
up=0; for i in $(seq 1 80); do sleep 15; curl -s localhost:8001/v1/models | grep -q gemma && { up=1; break; }; kill -0 $SERVER 2>/dev/null || break; done
off=$(grep -o "Total CPU offloaded parameters: [0-9.]*" ~/v019_serve_31b.log | tail -1 | grep -o "[0-9.]*$")
kv=$(grep -o "GPU KV cache size: [0-9,]* tokens" ~/v019_serve_31b.log | tail -1)
if [ $up = 1 ]; then b=$(bash ~/v019_bench.sh); else b="FAILED: $(grep -h -E '^[^ ]*(Error|error):|Error: ' ~/v019_serve_31b.log | grep -v WARNING | tail -1 | cut -c1-220)"; fi
echo "TRIAL ${TAG:-?} | BACKEND=${OFFLOAD_BACKEND:-prefetch} MAX_LEN=${MAX_LEN:-32768} G=${GROUP:-3}/${GROUP_N:-2} PF=${PREFETCH:-2} PIN=${PIN:-1} KV=${KV_DTYPE:-auto} OFFLOAD_GB=${OFFLOAD_GB:-} EAGER=${EAGER:-0} MAX_LEN=${MAX_LEN:-32768} | offloaded=${off:-?}GiB ${kv} | $b" >> ~/v019_trials.log
cp ~/v019_serve_31b.log ~/v019_serve_31b.${TAG:-x}.log
[ "${KEEP:-0}" = "1" ] && wait $SERVER || { kill $SERVER 2>/dev/null; pkill -f "vllm.entrypoints.openai.api_server"; }
