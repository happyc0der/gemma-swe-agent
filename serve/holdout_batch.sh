#!/bin/bash
# usage: holdout_batch.sh <variant> <results-name> <max-min> <max-calls> [extra swelite args...]
export DOCKER_CONFIG=$HOME/.docker-ssh
V=$1; R=$2; MIN=$3; CALLS=$4; shift 4
H=$(ip route | awk '/default/ {print $3}')
API=${API_BASE:-http://$H:11435/v1}; MODEL=${SERVED_MODEL:-gemma4:12b-32k}
cd ~/Projects/gemma-swe-agent/harness && rm -rf results/$R
IDS=$(python3 -c "import json; s=json.load(open('../experiments/splits.json')); print(' '.join('--task-id '+i for i in s['holdout'] if i not in s['env_unstable']))")
.venv/bin/swelite eval --data-dir ../data/competition --submission-dir ../experiments/variants/$V --results-dir results/$R \
  --api-base $API --served-model $MODEL --concurrency 2 $IDS \
  --max-time-minutes $MIN --max-tool-calls $CALLS "$@" > results/$R.console 2>&1
echo BATCH_DONE >> results/$R.console
