# TPU kernel v1 (dankaxon/gemma4-tpu-eval, TpuV5E8): VM died, no output

- Pushed 2026-10-29 ~03:00 UTC; QUEUED ~21 h (Kaggle shows no queue position); RUNNING from ~00:05 UTC 10-30;
  status ERROR by 01:29 UTC. `kaggle quota`: 1.25 TPU h used.
- `kaggle kernels output` returns no files and an empty log, and the kernel page is private (not readable signed out).
  Even the machine report printed in the first second is missing, so the session itself went down rather than
  Python raising (a Python error still leaves the log and /kaggle/working).
- Likeliest causes, from v1's code: the 62.6 GB bf16 checkpoint and both venvs were written to whichever of
  /tmp, /kaggle/tmp, /kaggle/working, /root, / had the most free space. A RAM-backed /tmp (tmpfs) would hold the
  weights in host RAM and vLLM then loads them again; /kaggle/working has a 20 GB output limit. Either can take the
  VM down. Not confirmed: there is no log.

v2 changes (kaggle/eval_tpu/run.py):
- Records the machine first (nproc, free, df -hT, the relevant /proc/mounts lines) into run.log and result.json.
- Puts weights, HF cache and both venvs under <disk>/gemma-work on a real (non-tmpfs) disk with >= 75 GB free,
  never /kaggle/working; a RAM disk only if no real disk fits.
- A resource thread logs MemAvailable and disk free every 30 s to res.log (stdout every 5 min or when < 24 GB),
  and kills vLLM if MemAvailable < 6 GB, writing the verdict, so the session ends normally and keeps its logs.
- Smoke-tested stage 0 in a Linux container with a 2 GB tmpfs /tmp: /tmp and /kaggle/working are skipped.
