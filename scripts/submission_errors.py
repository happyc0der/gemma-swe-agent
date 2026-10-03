"""List our competition submissions with score, size and the error text the Kaggle CLI hides.

`kaggle competitions submissions` shows a failed submission as COMPLETE with a blank score; the API's
`errorDescription` field holds the actual message. Run with the kaggle tool's own interpreter, e.g.
    ~/.local/share/uv/tools/kaggle/bin/python scripts/submission_errors.py
"""
from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()
for s in api.competition_submissions("gemma-4-developer-agent"):
    d = s.to_dict() if hasattr(s, "to_dict") else vars(s)
    print(f"{(d.get('date') or '')[:16]}  score={d.get('publicScore') or '-':5}  bytes={d.get('totalBytes') or 0:6}  "
          f"{(d.get('description') or '')[:60]}" + (f"\n    ERROR: {d['errorDescription']}" if d.get("errorDescription") else ""))
