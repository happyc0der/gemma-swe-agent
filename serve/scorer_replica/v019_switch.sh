#!/bin/bash
# Stop the 12B proxy server and start the vLLM 0.19.1 real-31B server (port 8001); stay alive while it runs.
pkill -f "vllm.entrypoints.openai.api_server" ; pkill -f "vllm serve"; sleep 10
rm -f ~/v019_serve_31b.status
bash ~/v019_serve_31b.sh &
SERVER=$!
for i in $(seq 1 120); do sleep 15; if curl -s localhost:8001/v1/models | grep -q gemma; then echo "V019_UP after $((i*15))s" >> ~/v019_serve_31b.status; break; fi; kill -0 $SERVER 2>/dev/null || { echo "V019_DIED" >> ~/v019_serve_31b.status; exit 1; }; done
grep -q V019_UP ~/v019_serve_31b.status || echo "V019_TIMEOUT" >> ~/v019_serve_31b.status
wait $SERVER; echo "V019_EXIT rc=$?" >> ~/v019_serve_31b.status
