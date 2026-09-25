#!/bin/bash
# Same as run_vllm_holdout.sh but over the dev split (~75 usable tasks).
export SPLIT=dev
exec bash ~/Projects/gemma-swe-agent/serve/run_vllm_holdout.sh "$@"
