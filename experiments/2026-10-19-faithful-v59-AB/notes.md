# Faithful eval: v5.9 on set AB (all 33 holdout tasks), kernel v20

Kernel v20, pushed 10-19 13:09 UTC, started 18:11 UTC (queued ~5 h), ALL_DONE 22:21 UTC (4.16 GPU h). Harness
swegemma 0.2.11 / adk_submission 0.2.13 (wheelhouse of 2026-10-12), llama.cpp 71ad0590f, canary passed
(fastapi_14303 solved at 9 calls), 4 GB `ulimit -v` cap on sandbox commands. No OOM kill or llama-server restart
this run (run.log has no oom/killed/restart lines). Raw results: `data/faithful_results/v59-AB/`.

v5.9 = v5.8 with the fix-script template reshaped into a fixed two-line `edit(p, old, new)` helper plus one
`edit('path', r'''old''', r'''new''')` call per change, no comments allowed, "only an ok line means the file changed".
Goal: turn the silent no-op fix scripts of v5.8 (28 of 70) into loud failures.

## Result vs v5.8 (kernel v19, the shipped config)

| | v5.8 (v19) | v5.9 (v20) |
|---|---|---|
| solved, 33 tasks | **14/33** | 12/33 |
| gained vs v5.8 | | requests_7205 (edit at call 5, solved at 11) |
| lost vs v5.8 | | fastapi_14485 (25 identical empty greps), fastapi_15589 (11 repro rewrites, first edit at call 39), fastapi_5624 (edit at 24 ok, then a stale second edit and an edit of a file never read both failed; incomplete patch) |
| no-edit tasks | 3 | 3 (fastapi_14485, fastapi_15023, rich_3938) |
| exact repeat calls | 128 of 935 (14%) | 146 of 977 (15%) |
| repeat searches of a dead term | 17 | 41 (fastapi_14485 alone ~25) |
| session timeouts | 5 | 2 (fastapi_13713, rich_3278) |
| median first edit (call #) | 15 | 18 |
| median output tokens/step | 35 | 34 |
| agent time | 228 min | 214 min |

### Fix scripts (`cat > /tmp/fix.py` heredocs)

| | v5.8 | v5.9 |
|---|---|---|
| scripts | 70 | 76 |
| printed `ok` (file changed) | 34 (49%) | 36 (47%) |
| silent no-op (exit 0, no ok, no error) | 29 | 4 |
| failed with a traceback | 7 (assert) | 36 (35 `assert n == 1`, 1 SyntaxError) |
| scripts containing comment lines | 41 | 19 |
| identical script rerun after a failure | 5 | 23 |

**Decision: not shipped.** 12/33 vs 14/33. The template did what it was designed to do (silent no-ops 29 -> 4, a
half-written script now raises), but the scripts that used to do nothing now fail their assert instead, and the
share of scripts that actually change the file is unchanged (47% vs 49%). The three losses are known coin-flip
modes, not something v5.9 introduced; the two tasks with 29 of the 35 assert failures (rich_3278: 22, rich_3535: 7)
have never been solved by any variant.

## What the assert failures are
Only 12 distinct scripts failed; the other 23 failures were the model re-running an unchanged script after the
traceback (the prompt forbids this; the traceback carries no information it can act on). Causes of the 12:
- 6: the old block IS in a displayed `sed -n` region, but its indentation differs (the model re-indents when copying,
  typically dropping the leading level). `s.count(old)` is exact, so these fail.
- 2: stale: the model had already edited those lines with an earlier ok script (fastapi_5624 call 27, after the ok at
  24) and quoted the original text again.
- 1: literal `\n` escapes inside the r''' string instead of newlines (fastapi_13713; the prompt forbids it).
- 2: file read, but the old block does not correspond to any displayed region (paraphrased from memory).
- 1: file never read at all (fastapi_5624 call 35, fastapi/routing.py).
What the model does on the call after a failure: identical rerun 17, sed/grep 10, a different script 4, submit 3.

## Next (v6.0)
v6.0 = v5.9 with a five-line helper instead of two: it matches old against the file line by line ignoring
indentation and re-indents new by the same offset (rescues the 6 indentation cases without a round trip), and on a
miss prints `FAIL <file> <n> matches; the file really has at lines A - B:` followed by the file's current lines at
the closest spot (so the stale and paraphrased cases, and the 23 blind reruns, get the real text to copy). Exit
stays 0 on FAIL so the printed lines reach the model. Cost: the helper is ~710 characters (~170 tokens) per script
instead of ~130, which at the T4's ~4 tokens/s is about +40 s per script in this eval (far less on the scorer's
vLLM); the eval therefore under-states v6.0 slightly. Kernel v21 runs it on AB; ship rule vs v5.8 14/33.
