#!/bin/zsh
# Run by the LaunchAgent com.happyc0der.gemma-submit daily at 20:05 local (00:05 UTC in EDT).
# 1. If .submit_ready exists (line 1 = message, optional line 2 = directory, default submission/), submit it and
#    delete the marker on success. This is the reviewed config staged for the day.
# 2. Otherwise the first file in .submit_queue/ (sorted by name; same format), deleted on success.
# 3. Otherwise, if .submit_fallback exists (same format), submit that and keep it. It points at the best proven
#    config, so a day with nothing staged still yields a replicate instead of a wasted slot.
# DRYRUN=1 prints what would be submitted without submitting.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd "$HOME/Projects/gemma-swe-agent" || exit 1
LOG=experiments/submit_daily.log
QUEUED=$(find .submit_queue -type f 2>/dev/null | sort | head -1)
if [ -f .submit_ready ]; then SRC=.submit_ready; KIND=staged
elif [ -n "$QUEUED" ]; then SRC=$QUEUED; KIND=queued
elif [ -f .submit_fallback ]; then SRC=.submit_fallback; KIND=fallback
else echo "[$(date -u)] no .submit_ready or .submit_fallback; nothing submitted" >> $LOG; exit 0; fi
MSG=$(sed -n 1p $SRC); DIR=$(sed -n 2p $SRC); DIR=${DIR:-submission}; SAFE=$(sed -n 3p $SRC)
# State of our most recent submission, from the API (the CLI hides errorDescription):
#   scored | pending (no score, no error) | kaggle_error (system error, capacity) | failed (any other error)
prev_state() {
  "$HOME/.local/share/uv/tools/kaggle/bin/python" - <<'PY' 2>/dev/null
from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi(); api.authenticate()
d = api.competition_submissions("gemma-4-developer-agent")[0].to_dict()
err = (d.get("errorDescription") or "").lower()
if d.get("publicScore"): print("scored")
elif not err: print("pending")
elif "system error" in err or "resources than are available" in err: print("kaggle_error")
else: print("failed")
PY
}
# Kaggle allows one pending submission per team; wait for the previous one to finish (until 23:30 UTC today).
state=$(prev_state)
while [ "$state" = "pending" ] && [ "${DRYRUN:-0}" != "1" ] && [ "$(date -u +%H%M)" -lt 2330 ]; do
  echo "[$(date -u)] previous submission still pending; waiting 30 min" >> $LOG; sleep 1800; state=$(prev_state)
done
# Optional line 3: a more conservative directory, used only when the previous run failed for a reason that could be
# ours (timeout or unhandled error), not when it is still pending or failed on Kaggle's side.
if [ -n "$SAFE" ] && [ "$state" = "failed" ]; then DIR=$SAFE; MSG="$MSG [conservative: previous run failed]"; fi
[ -f "$DIR/agent.yaml" ] || { echo "[$(date -u)] $KIND: $DIR/agent.yaml missing; nothing submitted" >> $LOG; exit 1; }
if [ "${DRYRUN:-0}" = "1" ]; then echo "DRYRUN $KIND: dir=$DIR msg=$MSG"; exit 0; fi
rm -f submission.zip && (cd "$DIR" && zip -qr "$OLDPWD/submission.zip" . -x '.*' -x 'prompts/system_v*.md')
out=$(kaggle competitions submit -c gemma-4-developer-agent -f submission.zip -m "$MSG" 2>&1); rc=$?
echo "[$(date -u)] $KIND rc=$rc dir=$DIR $out" >> $LOG
if [ $rc -eq 0 ] && echo "$out" | grep -q "Successfully submitted"; then
  printf '| %s | %s @ %s | %s | pending | submitted by LaunchAgent (%s) |\n' "$(date -u +%Y-%m-%d\ %H:%M)" "$DIR" "$(git rev-parse --short HEAD)" "$MSG" "$KIND" >> experiments/kaggle_submissions.md
  [ "$KIND" = staged ] && rm -f .submit_ready
  [ "$KIND" = queued ] && rm -f "$SRC"
fi
