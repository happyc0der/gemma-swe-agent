#!/bin/zsh
# Unattended: wait for the Kaggle dataset zip, unpack it, run the full gold/null harness sweeps, resume the Ollama proxy pull.
set -u
ROOT=~/Projects/gemma-swe-agent
DATA=$ROOT/data/competition
LOG=$DATA/after_download.log
exec >> $LOG 2>&1
echo "[$(date)] waiting for download to finish"
while pgrep -f "kaggle competitions download gemma-4-developer-agent" >/dev/null; do sleep 30; done
echo "[$(date)] download process exited; testing zip"
cd $DATA
if ! unzip -tq gemma-4-developer-agent.zip >/dev/null; then echo "[$(date)] ZIP CORRUPT, aborting"; exit 1; fi
unzip -n -q gemma-4-developer-agent.zip -x 'wheels/*' 'docker/*' 'sandbox/*' 'sample_submission/*' 'HARNESS_README.md' 'tasks.jsonl'
echo "[$(date)] unpacked: $(ls snapshots | wc -l) snapshots, $(ls graphs | wc -l) graphs, $(ls embeddings | wc -l) embeddings"
cd $ROOT/harness
rm -rf results/gold-all results/null-all
echo "[$(date)] gold sweep"
.venv/bin/swelite verify-gold --data-dir ../data/competition --results-dir results/gold-all --concurrency 4 > results/gold-all.console 2>&1
echo "[$(date)] null sweep"
.venv/bin/swelite verify-gold --null --data-dir ../data/competition --results-dir results/null-all --concurrency 4 > results/null-all.console 2>&1
echo "[$(date)] gold: $(python3 -c "import json;d=json.load(open('results/gold-all/summary.json'));print(d['resolved'],'/',d['total'])")  null: $(python3 -c "import json;d=json.load(open('results/null-all/summary.json'));print(d['resolved'],'/',d['total'],'(should be 0)')")"
echo "[$(date)] resuming ollama pull gemma4:12b"
ollama pull gemma4:12b >/dev/null 2>&1 && echo "[$(date)] ollama pull done" || echo "[$(date)] ollama pull failed"
echo "[$(date)] ALL DONE"
