#!/bin/zsh
# Run by the LaunchAgent com.happyc0der.gemma-submit daily at 20:05 local (00:05 UTC in EDT).
# 1. If .submit_ready exists (line 1 = message, optional line 2 = directory, default submission/), submit it and
#    delete the marker on success. This is the reviewed config staged for the day.
# 2. Otherwise, if .submit_fallback exists (same format), submit that and keep it. It points at the best proven
#    config, so a day with nothing staged still yields a replicate instead of a wasted slot.
# DRYRUN=1 prints what would be submitted without submitting.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd "$HOME/Projects/gemma-swe-agent" || exit 1
LOG=experiments/submit_daily.log
if [ -f .submit_ready ]; then SRC=.submit_ready; KIND=staged
elif [ -f .submit_fallback ]; then SRC=.submit_fallback; KIND=fallback
else echo "[$(date -u)] no .submit_ready or .submit_fallback; nothing submitted" >> $LOG; exit 0; fi
MSG=$(sed -n 1p $SRC); DIR=$(sed -n 2p $SRC); DIR=${DIR:-submission}
[ -f "$DIR/agent.yaml" ] || { echo "[$(date -u)] $KIND: $DIR/agent.yaml missing; nothing submitted" >> $LOG; exit 1; }
if [ "${DRYRUN:-0}" = "1" ]; then echo "DRYRUN $KIND: dir=$DIR msg=$MSG"; exit 0; fi
rm -f submission.zip && (cd "$DIR" && zip -qr "$OLDPWD/submission.zip" . -x '.*' -x 'prompts/system_v*.md')
out=$(kaggle competitions submit -c gemma-4-developer-agent -f submission.zip -m "$MSG" 2>&1); rc=$?
echo "[$(date -u)] $KIND rc=$rc dir=$DIR $out" >> $LOG
if [ $rc -eq 0 ] && echo "$out" | grep -q "Successfully submitted"; then
  printf '| %s | %s @ %s | %s | pending | submitted by LaunchAgent (%s) |\n' "$(date -u +%Y-%m-%d\ %H:%M)" "$DIR" "$(git rev-parse --short HEAD)" "$MSG" "$KIND" >> experiments/kaggle_submissions.md
  [ "$KIND" = staged ] && rm -f .submit_ready
fi
