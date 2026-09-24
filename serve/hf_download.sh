#!/bin/bash
# usage: hf_download.sh <repo_id> <dest_dir>   (plain HTTPS, no token; checkpoints are ungated)
REPO=$1; DEST=$2; mkdir -p "$DEST"; cd "$DEST"
python3 - "$REPO" > download.log 2>&1 <<'PY'
import sys, json, urllib.request, os, time
repo=sys.argv[1]
info=json.load(urllib.request.urlopen(f"https://huggingface.co/api/models/{repo}"))
files=[s["rfilename"] for s in info["siblings"]]
for f in files:
    if os.path.exists(f): print("skip", f, flush=True); continue
    url=f"https://huggingface.co/{repo}/resolve/main/{f}"
    os.makedirs(os.path.dirname(f) or ".", exist_ok=True)
    t=time.time()
    with urllib.request.urlopen(url) as r, open(f+".part","wb") as out:
        n=0
        while True:
            chunk=r.read(1<<22)
            if not chunk: break
            out.write(chunk); n+=len(chunk)
    os.replace(f+".part", f); print(f"{f} {n/1e6:.0f} MB {n/1e6/(time.time()-t):.1f} MB/s", flush=True)
print("HF_DOWNLOAD_DONE", flush=True)
PY
