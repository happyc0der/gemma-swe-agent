#!/bin/bash
# usage: hf_download.sh <repo_id> <dest_dir>   (plain HTTPS, no token; checkpoints are ungated)
# Verifies sizes against the HF manifest and resumes partial files with Range requests.
REPO=$1; DEST=$2; mkdir -p "$DEST"; cd "$DEST"
python3 - "$REPO" >> download.log 2>&1 <<'PY'
import sys, json, urllib.request, os, time
repo=sys.argv[1]
info=json.load(urllib.request.urlopen(f"https://huggingface.co/api/models/{repo}?blobs=true"))
files={s["rfilename"]: int(s.get("size") or 0) for s in info["siblings"]}
for f, size in files.items():
    url=f"https://huggingface.co/{repo}/resolve/main/{f}"
    os.makedirs(os.path.dirname(f) or ".", exist_ok=True)
    if os.path.exists(f) and os.path.getsize(f) == size:
        print("ok", f, flush=True); continue
    part = f + ".part"
    if os.path.exists(f):  # truncated earlier: treat as partial
        os.replace(f, part)
    for attempt in range(1, 21):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if have >= size and size > 0:
            break
        req = urllib.request.Request(url, headers={"Range": f"bytes={have}-"} if have else {})
        t = time.time(); n = 0
        try:
            with urllib.request.urlopen(req, timeout=120) as r, open(part, "ab") as out:
                if have and r.status != 206:
                    out.seek(0); out.truncate(); have = 0
                while True:
                    chunk = r.read(1 << 22)
                    if not chunk: break
                    out.write(chunk); n += len(chunk)
        except Exception as e:
            print(f"retry {attempt} {f} at {have/1e6:.0f} MB: {type(e).__name__}", flush=True); time.sleep(10); continue
        print(f"{f}: +{n/1e6:.0f} MB in {time.time()-t:.0f}s (now {os.path.getsize(part)/1e6:.0f}/{size/1e6:.0f} MB)", flush=True)
    if os.path.getsize(part) == size:
        os.replace(part, f); print("done", f, flush=True)
    else:
        print("FAILED size mismatch", f, os.path.getsize(part), size, flush=True)
bad=[f for f,s in files.items() if not (os.path.exists(f) and os.path.getsize(f)==s)]
print("HF_DOWNLOAD_DONE" if not bad else f"HF_DOWNLOAD_INCOMPLETE {bad}", flush=True)
PY
