#!/bin/bash
# Decode speed of the 31B replica: 128 generated tokens, thinking off, after one warm-up request.
Q='{"model":"gemma-4-31b-it-qat-w4a16-ct","max_tokens":MT,"temperature":0,"ignore_eos":true,"chat_template_kwargs":{"enable_thinking":false},"messages":[{"role":"user","content":"Write a long story about a lighthouse."}]}'
curl -s -m 600 localhost:8001/v1/chat/completions -H 'Content-Type: application/json' -d "${Q/MT/8}" >/dev/null
s=$(date +%s.%N); r=$(curl -s -m 900 localhost:8001/v1/chat/completions -H 'Content-Type: application/json' -d "${Q/MT/128}"); e=$(date +%s.%N)
n=$(echo "$r" | python3 -c "import json,sys; print(json.load(sys.stdin)['usage']['completion_tokens'])" 2>/dev/null || echo 0)
python3 -c "print('BENCH: %s tokens in %.1fs = %.2f tok/s' % ($n, $e-$s, $n/max($e-$s,1e-9)))"
