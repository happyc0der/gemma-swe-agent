# Faithful eval: v5.4 on set AB (all 33 holdout tasks), kernel v15

Kernel v15, 10-14 13:07 UTC to 17:22 UTC (4.24 GPU h, ALL_DONE). Harness swegemma 0.2.11 / adk_submission 0.2.13
(wheelhouse of 2026-10-12), llama.cpp 71ad0590f, canary passed (fastapi_14303 solved, median 34 tokens/step), 4 GB
`ulimit -v` cap on sandbox commands. Raw results: `data/faithful_results/v54-AB/`.

v5.4 = v5.0n with the procedure reordered: edit before any script, then write ONE /tmp/check.py and only rerun it.

## Result vs v5.0n (new harness: v13 set A + v12 set B)

| | v5.0n | v5.4 (v15) |
|---|---|---|
| solved, 33 tasks | 13/33 | **13/33** |
| changed tasks | fastapi_12942 solved | fastapi_14964 solved (the FastAPIDeprecationWarning task v5.3 targeted) |
| no-edit tasks | 4 | **11** |
| median call of first edit | 17 (A) / 24 (B) | 31 |
| exact repeat calls | 184 of 1061 (17%) | 133 of 1050 (13%) |
| `sed -n` read calls | 308 of 1061 (29%) | 341 of 1050 (32%) |
| session timeouts | 4 | 4 |
| median output tokens/step | 34-36 | 35 |

**Decision: ties on solves and adds a failure mode (11 tasks never edited), so v5.4 does not meet the ship rule;
v5.0n stays the submission.**

## What happened
Forbidding scripts before the first edit removed the repro loops but not the hesitation: the model replaced them with
search/read loops. fastapi_15023 ran 35 greps over docs_src without an edit; fastapi_13713 paged
fastapi/applications.py 50 lines at a time from line 48 to 850, then paged the same range again (37 sed calls, one
edit at call 41); fastapi_14246 repeated `grep -n "def get_schema_from_model_field"` three times. Ordering rules move
the waste, they do not remove it (consistent with earlier lessons on checkpoint rules).

## Other observations
- llama-server was OOM-killed once (16:50, during rich_3480, rc=-9) and restarted by the watchdog; host RAM sits at
  28-29 GB used for most of the run, so the 4 GB per-command cap does not leave enough headroom. The run completed
  (rich_3480 unsolved by every prompt so far). Possible fix if it recurs: cap at 2-3 GB for verification of
  rich_3480 or drop page cache; not changed today.
- fastapi_14583 ended with "Sandbox execution error: Unterminated string ..." from the harness (a malformed tool
  call); v5.0n also fails this task.

## Next (v5.5)
About 30% of every config's calls are `sed -n` reads of at most 60 lines. The harness's `read_file` tool (up to 150
lines / 10,000 chars, used by the public 0.22-0.24 bundles) was dropped on 09-26 only because of a 12B-proxy schema
bug that the scorer stack does not have (experiments/2026-09-27-day4/notes.md, correction). v5.5 = v5.0n +
`read_file` (prompt: always pass start/end lines, at most 100 lines per call). Eval: kernel v16 on AB.
