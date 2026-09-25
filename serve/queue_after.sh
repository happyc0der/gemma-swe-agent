#!/bin/bash
# usage: queue_after.sh <results-name-to-wait-for> <variant> <results-name> <max-min> <max-calls>
# Waits for BATCH_DONE of a running holdout, then launches the next one on vLLM.
WAIT=$1; shift
until grep -q BATCH_DONE ~/Projects/gemma-swe-agent/harness/results/$WAIT.console 2>/dev/null; do sleep 60; done
cd ~/Projects/gemma-swe-agent && git pull -q
exec bash ~/Projects/gemma-swe-agent/serve/run_vllm_holdout.sh "$@"
