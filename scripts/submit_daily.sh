#!/bin/zsh
# Unattended daily Kaggle submission of ./submission at the next 00:05 UTC. Usage: scripts/submit_daily.sh "<message>"
set -u
ROOT=~/Projects/gemma-swe-agent; cd $ROOT
MSG=${1:-"daily submission"}
LOG=$ROOT/experiments/submit_daily.log
now=$(date -u +%s); target=$(( (now/86400 + 1)*86400 + 300 ))   # next UTC midnight + 5 min
echo "[$(date -u)] scheduled for $(date -u -r $target) : $MSG" >> $LOG
sleep $(( target - now ))
harness/.venv/bin/swelite validate submission >> $LOG 2>&1 || { echo "[$(date -u)] validate FAILED, not submitting" >> $LOG; exit 1; }
rm -f submission.zip && (cd submission && zip -qr ../submission.zip . -x '.*')
out=$(kaggle competitions submit -c gemma-4-developer-agent -f submission.zip -m "$MSG" 2>&1); rc=$?
echo "[$(date -u)] submit rc=$rc: $(echo $out | tail -c 300)" >> $LOG
printf '| %s | %s | %s | pending | scheduled by submit_daily.sh |\n' "$(date -u +%Y-%m-%d\ %H:%M)" "submission/ @ $(git rev-parse --short HEAD)" "$MSG" >> experiments/kaggle_submissions.md
