#!/bin/bash
# usage: run_vllm_holdout.sh <variant-or-../../submission> <results-name> <max-min> <max-calls>
# Runs the holdout split against the local vLLM proxy (port 8000). Launch via schtasks so it survives SSH logoff.
export API_BASE=http://127.0.0.1:8000/v1 SERVED_MODEL=gemma-4-12b-it-qat-w4a16-ct
exec bash ~/Projects/gemma-swe-agent/serve/holdout_batch.sh "$@"
