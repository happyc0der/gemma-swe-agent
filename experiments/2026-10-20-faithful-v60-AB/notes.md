# Faithful eval: v6.0 on set AB (all 33 holdout tasks), kernel v21

Kernel v21, pushed 10-20 13:17 UTC, started at once, ALL_DONE 17:44 UTC (4.46 GPU h; agent time 232 min). Harness
swegemma 0.2.11 / adk_submission 0.2.13 (wheelhouse of 2026-10-12), llama.cpp 71ad0590f, canary passed
(fastapi_14303 solved at 13 steps). One llama-server restart (host RAM at 32 GB during rich_3480, the watchdog
recovered). Raw results: `data/faithful_results/v60-AB/`.

v6.0 = v5.9 with a five-line `edit()` helper: line-wise match ignoring indentation, re-indents `new` by the same
offset, and on a miss prints `FAIL <file> <n> matches; the file really has at lines A - B:` plus the file's current
lines (exit 0, so the model sees them). Goal: rescue the indentation-only misses and the blind reruns of v5.9.

## Result vs v5.8 (kernel v19, the conservative fallback) and v5.9 (kernel v20)

| | v5.8 (v19) | v5.9 (v20) | v6.0 (v21) |
|---|---|---|---|
| solved, 33 tasks | **14/33** | 12/33 | **14/33** |
| vs v5.8 | | -3 +1 | gained requests_7205 (edit at call 5), lost fastapi_15589 (first real edit at call 33, right after the budget warning; the 27-call FAIL came from a stale block) |
| no-edit tasks | 3 | 3 | 2 |
| exact repeat calls | 128 of 935 (14%) | 146 of 977 (15%) | **95 of 936 (10%)** |
| repeat searches of a dead term | 17 | 41 | 21 |
| session timeouts | 5 | 2 | 5 |
| median first edit (call #) | 15 | 18 | 21 |
| median output tokens/step | 35 | 34 | 34 |
| agent time | 228 min | 214 min | 232 min |

### Fix scripts (`cat > /tmp/fix.py` heredocs, then `python3 /tmp/fix.py`)

| | v5.8 | v5.9 | v6.0 |
|---|---|---|---|
| scripts | 70 | 76 | 75 |
| printed `ok` (file changed) | 34 (49%) | 36 (47%) | 38 (51%) |
| silent no-op | 29 | 5 | 4 |
| failed loudly | 7 tracebacks | 35 asserts | 33 `FAIL` lines (31 "0 matches", 2 "2 matches") |
| distinct failing scripts | 7 | 12 | 16 |
| call after a failure | sed/grep 6 | same script 17, sed/grep 14, submit 3 | same script 15, sed/grep 15, submit 1 |
| failures in rich_3278 + rich_3535 (never solved by anyone) | 1 | 29 | 24 |

**Decision: not shipped.** 14/33 ties v5.8; the ship rule needs a result above it. The helper did what it was
built for (the model now sees the real lines; silent no-ops stay near zero; exact repeats fell to 10%), but the
share of scripts that change the file moved only 47% -> 51%, and 15 of the 33 FAILs were still followed by the
identical script, i.e. the printed lines are often not used. 24 of the 33 FAILs are in the two never-solved rich
tasks. Solved-set difference vs v5.8 is one coin flip each way.

Context: on 10-20 the daily LB submission switched to the public budget-fit bundle (thinking on, 8 min / 28 calls),
which this thinking-off eval cannot measure. v5.8 stays the conservative fallback (line 3 of `.submit_fallback`);
v6.0 is not promoted over it on a tie. The thinking-off eval is now used only to screen single-sentence ideas for
the budget-fit base (first: the official starter prompt itself, then + the budget-warning protocol, kernels v22/v23).
