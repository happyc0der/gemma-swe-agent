#!/bin/zsh
# Run by the LaunchAgent com.happyc0der.gemma-submit daily at 20:05 local (00:05 UTC in EDT).
# Submits ./submission only when a reviewed config has been marked ready:
#   echo "<submission message>" > .submit_ready
# The marker is consumed on success, so nothing is ever submitted twice or without review.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd "$HOME/Projects/gemma-swe-agent" || exit 1
LOG=experiments/submit_daily.log
[ -f .submit_ready ] || { echo "[$(date -u)] no .submit_ready marker; nothing submitted" >> $LOG; exit 0; }
MSG=$(head -1 .submit_ready)
rm -f submission.zip && (cd submission && zip -qr ../submission.zip . -x '.*')
out=$(kaggle competitions submit -c gemma-4-developer-agent -f submission.zip -m "$MSG" 2>&1); rc=$?
echo "[$(date -u)] rc=$rc $out" >> $LOG
if [ $rc -eq 0 ] && echo "$out" | grep -q "Successfully submitted"; then
  printf '| %s | submission/ @ %s | %s | pending | submitted by LaunchAgent |\n' "$(date -u +%Y-%m-%d\ %H:%M)" "$(git rev-parse --short HEAD)" "$MSG" >> experiments/kaggle_submissions.md
  rm -f .submit_ready
fi
