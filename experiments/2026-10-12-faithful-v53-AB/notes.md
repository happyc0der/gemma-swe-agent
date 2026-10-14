# Faithful eval: v5.3 on set AB (33 holdout tasks), kernel v14: killed by host OOM after 29 tasks

Kernel v14, 10-12 13:06 UTC to ~17:00 UTC (~3.9 GPU h; status ERROR). Harness swegemma 0.2.11 / adk_submission
0.2.13 (wheelhouse of 2026-10-09), llama.cpp 71ad0590f, canary passed (fastapi_14303 solved, median 36 tokens/step).
Raw results: `data/faithful_results/v53-AB/` (per-task files were recovered from the kernel output even though the
final .tgz step never ran).

## Why it died
During task 30 (rich_3480) the agent's own repro script doubled a Text object in a loop (`Length after 20 appends:
1048576`, then more appends). The subprocess sandbox has no memory cap, so the script took the kernel's 32 GB host
RAM and the eval process was OOM-killed ("Killed" in the kernel log). The scorer's Docker sandbox caps each task at
`mem_limit 4g`. Fix: `kaggle/faithful_sandbox.py` now runs every agent and verification command under
`ulimit -v` 4 GB (per-task pip/uv setup excepted). Tested in python:3.13-slim: the exponential script raises
MemoryError at 2^30 chars instead of eating RAM; threads, pip and pytest still work under the cap.
Not run: rich_3480, rich_3052, rich_3278, rich_3061 (v5.0n solves none of these four).

## Result vs v5.0n (new harness)

| | v5.0n (v13 set A + v12 set B) | v5.3 (v14) |
|---|---|---|
| solved, same 29 tasks | 13/29 | **13/29** |
| solved, 33 tasks | 13/33 | 13/29 + unknown 4 (v5.0n 0/4 on them) |
| changed tasks | fastapi_14485 solved | fastapi_15589 solved |
| no-edit tasks | 4 (on 33) | 6 (on 29) |
| exact repeat calls | 184 of 1061 (17%) | 189 of 969 (20%) |
| session timeouts | 4 | 2 |
| median output tokens/step | 34-36 | 34 |

The rule's target task, fastapi_14964 (should reuse FastAPIDeprecationWarning), still failed: 78 calls, timeout,
62 exact duplicate calls. One swap each way (15589 gained, 14485 lost) is noise.

**Decision: v5.3 does not meet the ship rule (ties at best, no clear gain); v5.0n stays the submission.**

## Where failed tasks lose their calls (input to v5.4)
Repro scripts written before the first edit, per task: solved 0.8 vs failed 4.5 (v5.3); solved 1.1 vs failed 5.4
(v5.0n set A). Calls before the first edit: solved 9.8 vs failed 28.2 (v5.3). Examples: rich_4075 rewrote
/tmp/repro.py 15 times (the last 8 identical) and never edited; fastapi_14246 10 rewrites, no edit; fastapi_15023 and
rich_3938 searched 30+ times without an edit. The prompt's "edit by the 10th call" and "stop reproducing after two
attempts" rules were ignored, as earlier checkpoint rules were. v5.4 changes the procedure order instead (edit
first, then write one check script).
