"""Submit a zip to the competition and print Kaggle's own error text on failure (the CLI prints only the HTTP status).

Usage: kaggle-python scripts/kaggle_submit.py FILE MESSAGE
Exit 0 and "Successfully submitted" on success; exit 2 and "HTTP <code>: <body>" on an HTTP error; exit 3 otherwise.
"""
import sys

import requests
from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()
try:
    r = api.competition_submit(sys.argv[1], sys.argv[2], "gemma-4-developer-agent", quiet=True)
    print(r.message)
    if r.message == api.COMPETITION_SUBMIT_UPLOAD_FAILED_MESSAGE:
        sys.exit(3)
    print("Successfully submitted")
except requests.exceptions.HTTPError as e:
    print(f"HTTP {e.response.status_code}: {e.response.text[:500]}")
    sys.exit(2)
except Exception as e:
    print(f"{type(e).__name__}: {str(e)[:500]}")
    sys.exit(3)
