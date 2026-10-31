# Kaggle TPU: faithful offline eval with thinking ON. The T4 kernel (kaggle/eval_faithful) can only screen thinking-off
# twins because llama.cpp on T4s decodes ~11 tok/s; the LB base thinks (4096-token budget). Here the 31B is served by
# vLLM itself (vllm-tpu: same OpenAI server, gemma4 tool-call and reasoning parsers as the scorer's vLLM 0.19.1) from
# the bf16 QAT checkpoint (google/gemma-4-31B-it-qat-q4_0-unquantized, the weights the scorer's w4a16 model quantizes).
# Stage 1 (this file, Kaggle's python): env report, two venvs (vllm-tpu; official harness), weights, vLLM server,
#   checks (thinking off/on, thinking budget, tool-call parsing) and a decode/prefill benchmark.
# Stage 2 (kaggle/eval_tpu/eval_stage.py in the harness venv): canary + each variant on the holdout subset through the
#   official Evaluator, max_time_minutes scaled by scorer_decode_tps / measured decode tok/s.
import json, os, shutil, subprocess, sys, threading, time, urllib.request
T0 = time.time()
CFG = {"variants": ["experiments/variants/pub-budget-fit", "experiments/variants/bf-nomatch"], "subset": "AB",
       "n_per_repo": {"fastapi/fastapi": 8, "psf/requests": 4, "Textualize/rich": 4},
       "scorer_decode_tps": 33.0, "session_budget_h": 8.5, "probe_only": False, "vllm": "vllm-tpu==0.32.0",
       "diag_exit_min": 45}   # > 0: stop everything and exit cleanly after this many minutes (see the note at step 0)
os.makedirs("/kaggle/working", exist_ok=True)
LOG = open("/kaggle/working/run.log", "a", buffering=1)
def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a); print(s, flush=True); LOG.write(s + "\n")
def sh(cmd, timeout=None):
    log("$", cmd[:240]); r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    out = (r.stdout[-2000:] + ("\n" + r.stderr[-2000:] if r.stderr.strip() else "")).strip()
    if out: log(out)
    return r
RESULT = {"cfg": CFG}
def save():
    json.dump(RESULT, open("/kaggle/working/result.json", "w"), indent=1)

# 0. what machine is this. v1 (10-30) died after 1.25 TPU h with no output and no log at all, i.e. the VM itself went
# down; the likeliest causes are host RAM (62 GB of weights in a RAM-backed /tmp, then loaded again by vLLM) or the
# 20 GB /kaggle/working output limit. So: record the machine first, keep weights and venvs on a real disk outside
# /kaggle/working, and watch memory, stopping vLLM before the host runs out so the logs survive.
# v2 (10-31) died the same way after 1.30 TPU h (v1: 1.25 h), again with no files and an empty log, so the RAM guard
# never fired or its logs died with the session. /proc/meminfo shows the host, but a container is killed at its own
# cgroup limit, so the guard now also watches the cgroup's non-reclaimable memory (anon + shmem). And while the cause is
# unknown, diag_exit_min makes the run leave on its own well before the ~75 min mark, so Kaggle saves run.log, res.log
# and result.json and we learn how far it got (venvs, download, vLLM load) and what memory looked like.
r = sh("python3 --version; nproc; free -g; df -hT 2>/dev/null | head -30; grep -E ' (/|/tmp|/kaggle[^ ]*|/root|/mnt[^ ]*) ' /proc/mounts; ls /dev/accel* /dev/vfio 2>&1 | head; env | grep -iE 'tpu|accel' | head -20; "
       "cat /proc/self/cgroup; for f in /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory/memory.limit_in_bytes /sys/fs/cgroup/pids.max; do echo $f $(cat $f 2>&1); done; ulimit -a | head -20")
RESULT["machine"] = r.stdout[-3000:]
def fstype(path):
    best, fs = "", "?"
    for line in open("/proc/mounts"):
        mnt, typ = line.split()[1:3]
        if (path == mnt or path.startswith(mnt.rstrip("/") + "/")) and len(mnt) > len(best): best, fs = mnt, typ
    return fs
cands = [p for p in ["/kaggle/tmp", "/tmp", "/root", "/mnt", "/"] if os.path.isdir(p)]
RESULT["disks"] = {p: {"fs": fstype(p), "free_gb": round(shutil.disk_usage(p).free / 1e9)} for p in cands + ["/kaggle/working"] if os.path.isdir(p)}
big = lambda ps: [p for p in ps if RESULT["disks"][p]["free_gb"] >= 75]   # weights 62.6 GB
real = [p for p in cands if RESULT["disks"][p]["fs"] not in ("tmpfs", "ramfs")]
disk = max(big(real) or big(cands) or cands, key=lambda p: RESULT["disks"][p]["free_gb"])   # a RAM disk only if no real one fits
W = os.path.join(disk, "gemma-work"); os.makedirs(W, exist_ok=True); VV, HV = f"{W}/vv", f"{W}/hv"
RESULT["disk"] = {"path": W, **RESULT["disks"][disk]}; log("disks", RESULT["disks"], "-> using", RESULT["disk"]); save()

server, cmd, STOP = None, None, {"oom": False}
def cgroup():   # (limit GB or None, non-reclaimable GB = anon + shmem, all charged GB incl. page cache) for cgroup v2 or v1
    for d, v2 in [("/sys/fs/cgroup", True), ("/sys/fs/cgroup/memory", False)]:
        try:
            st = {l.split()[0]: int(l.split()[1]) for l in open(f"{d}/memory.stat")}
            lim = open(f"{d}/memory.max" if v2 else f"{d}/memory.limit_in_bytes").read().strip()
            lim = None if lim == "max" or int(lim) > 1 << 60 else int(lim) / 2**30
            hard = st.get("anon", 0) + st.get("shmem", 0) if v2 else st.get("total_rss", st.get("rss", 0)) + st.get("total_shmem", st.get("shmem", 0))
            cur = int(open(f"{d}/memory.current" if v2 else f"{d}/memory.usage_in_bytes").read())
            return lim, hard / 2**30, cur / 2**30
        except Exception: pass
    return None, None, None
def resources():   # every 15 s to res.log (every 5 min also to stdout); kill vLLM before the host or the container runs out
    global server; i = 0
    while True:
        try:
            m = {l.split(":")[0]: int(l.split()[1]) // 1048576 for l in open("/proc/meminfo") if l.startswith(("MemTotal", "MemAvailable"))}
            lim, hard, cur = cgroup()
            room = min(m["MemAvailable"], lim - hard if lim else 1e9)
            line = (f"RES host avail {m['MemAvailable']}/{m['MemTotal']} GB | cgroup limit {lim and round(lim)} anon+shmem {hard and round(hard, 1)} "
                    f"charged {cur and round(cur, 1)} GB | room {round(room, 1)} GB | {W} free {shutil.disk_usage(W).free // 10**9} GB")
            if i % 4 == 0: line += " | du " + subprocess.run(f"du -sm {W}/gemma31 /kaggle/working 2>/dev/null | cut -f1 | tr '\\n' ' '", shell=True, capture_output=True, text=True, timeout=60).stdout.strip() + " MB"
            open("/kaggle/working/res.log", "a").write(time.strftime("%H:%M:%S ") + line + "\n")
            if i % 20 == 0 or room < 24: log(line)
            if room < 8 and server is not None and server.poll() is None:
                STOP["oom"] = True; server.kill(); log("LOW MEMORY: killed vLLM to keep the VM (and these logs) alive")
                RESULT["verdict"] = f"memory exhausted ({line})"; save()
        except Exception as e: log("RES error", repr(e)[:200])
        i += 1; time.sleep(15)
threading.Thread(target=resources, daemon=True).start()
def diag_exit():   # leave cleanly before the point where v1 and v2 died, so Kaggle saves this session's files
    time.sleep(CFG["diag_exit_min"] * 60)
    log(f"DIAG EXIT after {CFG['diag_exit_min']} min: stopping everything so the outputs are saved")
    try: sh(f"du -sm {W}/* 2>/dev/null; df -h {W} /kaggle/working | tail -2; free -g | head -2; ps aux --sort=-rss | head -8 | cut -c1-200", timeout=120)
    except Exception as e: log("diag report error", repr(e)[:200])
    RESULT["verdict"] = RESULT.get("verdict") or f"diag exit after {CFG['diag_exit_min']} min"; save()
    kids, doomed, todo = {}, set(), [os.getpid()]   # kill our whole process tree (pip/uv, the download, vLLM and its workers)
    for p in filter(str.isdigit, os.listdir("/proc")):   # plus anything else still running from W (e.g. reparented workers)
        try:
            kids.setdefault(int(open(f"/proc/{p}/stat").read().rsplit(")", 1)[1].split()[1]), []).append(int(p))
            if W in open(f"/proc/{p}/cmdline", "rb").read().decode(errors="ignore"): doomed.add(int(p))
        except Exception: pass
    while todo:
        for c in kids.get(todo.pop(), []): doomed.add(c); todo.append(c)
    for pid in doomed - {os.getpid()}:
        try: os.kill(pid, 9)
        except Exception: pass
    LOG.flush(); os._exit(0)
if CFG.get("diag_exit_min"): threading.Thread(target=diag_exit, daemon=True).start()

# 1. venvs: vllm-tpu (server) and the official harness (eval stage)
sh("python3 -m pip install -q uv 2>&1 | tail -1")
UV = shutil.which("uv") or os.path.expanduser("~/.local/bin/uv")
sh(f"{UV} venv -q -p 3.12 --seed {VV} && {UV} pip install -q --python {VV}/bin/python '{CFG['vllm']}' 2>&1 | tail -3", timeout=3600)
r = sh(f"{VV}/bin/python -c 'import vllm, jax; print(\"vllm\", vllm.__version__, \"jax\", jax.__version__, jax.devices())' 2>&1 | tail -3", timeout=900)
RESULT["vllm_import"] = r.stdout[-600:]; save()
sh("cd /kaggle/working && rm -rf gemma-swe-agent && git clone -q https://github.com/happyc0der/gemma-swe-agent.git && cd gemma-swe-agent && git log --oneline | head -1")
REPO = "/kaggle/working/gemma-swe-agent"

# 2. weights
if shutil.disk_usage(W).free < 75e9: log("GATE: < 75 GB free for the weights"); RESULT["verdict"] = "no disk"; save(); sys.exit(0)
os.environ["HF_HOME"] = f"{W}/hf"; os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
t = time.time()
sh(f"{VV}/bin/python -c \"from huggingface_hub import snapshot_download; print(snapshot_download('google/gemma-4-31B-it-qat-q4_0-unquantized', local_dir='{W}/gemma31'))\"", timeout=5400)
RESULT["download_s"] = round(time.time() - t); sh(f"du -sh {W}/gemma31; df -h {W} | tail -1; free -g | head -2"); save()

# 3. vLLM server, scorer flags (max_model_len 32768, gemma4 tool + reasoning parsers); TP over all chips
NAME = "gemma-4-31b-it-qat-w4a16-ct"; URL = "http://127.0.0.1:8000/v1"
def server_cmd(tp, limit_mm):
    c = [f"{VV}/bin/vllm", "serve", f"{W}/gemma31", "--served-model-name", NAME, "--tensor-parallel-size", str(tp),
         "--max-model-len", "32768", "--enable-auto-tool-choice", "--tool-call-parser", "gemma4", "--reasoning-parser", "gemma4",
         "--host", "127.0.0.1", "--port", "8000", "--max-num-seqs", "4", "--enable-prefix-caching"]
    return c + (["--limit-mm-per-prompt", '{"image": 0, "audio": 0, "video": 0}'] if limit_mm else [])
def start_server(cmd, tag, wait_s=5400):
    log("starting:", " ".join(cmd))
    global server
    srv = server = subprocess.Popen(cmd, stdout=open(f"/kaggle/working/vllm-{tag}.log", "a"), stderr=subprocess.STDOUT, env=os.environ)
    for i in range(wait_s // 15):
        time.sleep(15)
        try: urllib.request.urlopen(URL + "/models", timeout=5).read(); log(f"vLLM up ({tag}) after {(i+1)*15}s"); return srv
        except Exception:
            if srv.poll() is not None:
                log(f"vLLM died ({tag}):", open(f"/kaggle/working/vllm-{tag}.log").read()[-3000:]); return None
    srv.terminate(); log(f"vLLM not up after {wait_s}s ({tag})"); return None
r = sh(f"{VV}/bin/python -c 'import jax; print(len(jax.devices()), jax.devices()[0].device_kind)'", timeout=600)
try: n_chips, kind = int(r.stdout.split()[0]), " ".join(r.stdout.split()[1:])
except Exception: n_chips, kind = 8, "?"
RESULT["tpu"] = {"chips": n_chips, "kind": kind}; save()
for tp, mm in [(n_chips, True), (n_chips, False), (max(4, n_chips // 2), True)]:
    if STOP["oom"]: break
    cmd = server_cmd(tp, mm); t = time.time(); server = start_server(cmd, f"tp{tp}{'-mm0' if mm else ''}")
    if server: RESULT["server"] = {"cmd": cmd, "startup_s": round(time.time() - t)}; break
save()
if server is None: log("GATE: vLLM did not start on this TPU"); RESULT["verdict"] = RESULT.get("verdict") or "server failed"; save(); sys.exit(0)
sh("tail -5 /kaggle/working/vllm-*.log")

# 4. checks and benchmark
def chat(body, timeout=900):
    body = {"model": NAME, **body}
    req = urllib.request.Request(URL + "/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
def stream(body, timeout=1800):
    body = {"model": NAME, "stream": True, "stream_options": {"include_usage": True}, **body}
    req = urllib.request.Request(URL + "/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time(); first = None; usage = None
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for line in resp:
            line = line.decode().strip()
            if not line.startswith("data:") or line[5:].strip() == "[DONE]": continue
            j = json.loads(line[5:]); usage = j.get("usage") or usage
            d = (j.get("choices") or [{}])[0].get("delta") or {}
            if first is None and (d.get("content") or d.get("reasoning_content") or d.get("reasoning") or d.get("tool_calls")): first = time.time()
    t1 = time.time(); n = (usage or {}).get("completion_tokens", 0)
    return {"prompt_tokens": (usage or {}).get("prompt_tokens"), "completion_tokens": n, "ttft_s": round((first or t1) - t0, 2),
            "decode_tps": round((n - 1) / max(t1 - (first or t1), 1e-6), 1)}
OFF = {"chat_template_kwargs": {"enable_thinking": False}}
ON = {"chat_template_kwargs": {"enable_thinking": True}}
try:
    m = chat({"max_tokens": 60, "temperature": 0, "messages": [{"role": "user", "content": "Reply with the single word OK."}], **OFF})["choices"][0]["message"]
    RESULT["check_off"] = {"content": (m.get("content") or "")[:80], "reasoning": (m.get("reasoning_content") or m.get("reasoning") or "")[:80]}
    r = chat({"max_tokens": 2000, "temperature": 0, "messages": [{"role": "user", "content": "What is 17 * 23? Answer with the number."}], **ON})
    m = r["choices"][0]["message"]
    RESULT["check_on"] = {"content": (m.get("content") or "")[:80], "reasoning_chars": len(m.get("reasoning_content") or m.get("reasoning") or ""), "usage": r.get("usage")}
    r = chat({"max_tokens": 4000, "temperature": 0, "thinking_token_budget": 64, "messages": [{"role": "user", "content": "Prove that there are infinitely many primes, then state the result in one line."}], **ON})
    m = r["choices"][0]["message"]
    RESULT["check_budget64"] = {"reasoning_chars": len(m.get("reasoning_content") or m.get("reasoning") or ""), "usage": r.get("usage")}
    tools = [{"type": "function", "function": {"name": "read_file", "description": "Read a file in the repository.",
              "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "start_line": {"type": "integer"}}, "required": ["path"]}}}]
    r = chat({"max_tokens": 2000, "temperature": 0.2, "tools": tools, "messages": [{"role": "user", "content": "Use the tool to read lines from 10 of /workspace/setup.py."}], **ON})
    m = r["choices"][0]["message"]
    RESULT["check_tool"] = {"tool_calls": m.get("tool_calls"), "content": (m.get("content") or "")[:120], "finish": r["choices"][0].get("finish_reason")}
except Exception as e:
    RESULT["check_error"] = repr(e)[:600]
log("CHECKS", json.dumps({k: v for k, v in RESULT.items() if k.startswith("check")})[:3000]); save()
code = open(f"{REPO}/kaggle/faithful_sandbox.py").read() * 4   # ~6k tokens of real code
RESULT["bench"] = []
for tag, body in [("warm", {"max_tokens": 64, "messages": [{"role": "user", "content": "Say hi."}], **OFF}),
                  ("6k-prompt-300-out", {"max_tokens": 300, "min_tokens": 300, "temperature": 0.7, "messages": [{"role": "user", "content": code + "\nSummarize this code."}], **OFF}),
                  ("6k-prompt-300-out-cached", {"max_tokens": 300, "min_tokens": 300, "temperature": 0.7, "messages": [{"role": "user", "content": code + "\nSummarize this code."}], **OFF}),
                  ("thinking-1000", {"max_tokens": 1000, "min_tokens": 1000, "temperature": 1.0, "messages": [{"role": "user", "content": code + "\nFind a bug."}], **ON})]:
    try: b = stream(body); b["tag"] = tag; RESULT["bench"].append(b); log("BENCH", b)
    except Exception as e: log("BENCH error", tag, repr(e)[:300])
save()
tps = [b["decode_tps"] for b in RESULT["bench"] if b["tag"] != "warm" and b["completion_tokens"] > 100]
tps = sorted(tps)[len(tps) // 2] if tps else 0
scale = round(min(4.0, max(0.5, CFG["scorer_decode_tps"] / tps)), 2) if tps else 0
RESULT["decode_tps"] = tps; RESULT["time_scale"] = scale; log(f"decode {tps} tok/s -> time_scale {scale}"); save()
if CFG["probe_only"] or not tps or scale >= 4.0:
    RESULT["verdict"] = "probe done" if tps else "no benchmark"; save(); server.terminate(); sys.exit(0)

# 5. stage 2 in the harness venv, server kept alive by a watchdog
def watchdog():
    global server; n = 0
    while True:
        time.sleep(30)
        if STOP["oom"]: return
        if server.poll() is not None:
            n += 1; log(f"WATCHDOG: vLLM exited rc={server.returncode}; restarting"); server = start_server(cmd, f"restart{n}")
            if server is None: return
threading.Thread(target=watchdog, daemon=True).start()
sh(f"{UV} venv -q -p 3.12 --seed {HV}", timeout=600)
env = dict(os.environ, PATH=f"{HV}/bin:" + os.environ["PATH"], VIRTUAL_ENV=HV)
stage = {**CFG, "time_scale": scale, "t0": T0}
p = subprocess.run([f"{HV}/bin/python", f"{REPO}/kaggle/eval_tpu/eval_stage.py", json.dumps(stage)], env=env, cwd="/kaggle/working")
log(f"stage 2 exited rc={p.returncode}"); RESULT["verdict"] = f"stage 2 rc={p.returncode}"; save()
server.terminate(); log(f"ALL_DONE after {(time.time()-T0)/3600:.2f} h")
