#!/bin/bash
# usage: proxy_batch.sh <variant> <results-name> <max-min> <max-calls> [extra swelite args...]  -- runs 4 smoke tasks against the MSI Ollama proxy with thinking ON
export DOCKER_CONFIG=$HOME/.docker-ssh
V=$1; R=$2; MIN=$3; CALLS=$4; shift 4
H=$(ip route | awk '/default/ {print $3}')
API=${API_BASE:-http://$H:11435/v1}; MODEL=${SERVED_MODEL:-gemma4:12b-32k}
cd ~/Projects/gemma-swe-agent/harness && rm -rf results/$R
.venv/bin/swelite eval --data-dir ../data/competition --submission-dir ../experiments/variants/$V --results-dir results/$R \
  --api-base $API --served-model $MODEL --concurrency 2 \
  --task-id requests_7205 --task-id rich_2725 --task-id rich_3454 --task-id fastapi_11355 \
  --max-time-minutes $MIN --max-tool-calls $CALLS "$@" > results/$R.console 2>&1
echo BATCH_DONE >> results/$R.console
