# Faithful eval: prompt v5.0n vs v4.7-v4.9 (same 16 holdout tasks)

Kernel `dankaxon/gemma4-faithful-eval` v6, T4x2, 21:45-00:12 UTC (112 min of agent runs, 2.45 GPU h with setup).
Metrics: `python3 scripts/faithful_metrics.py <results dirs>`.

| metric | v4.7 | v4.8 | v4.9 | v5.0n |
|---|---|---|---|---|
| solved | 8 | 8 | 7 | **9** (all 8 earlier solves kept, plus fastapi_12942, never solved before) |
| tasks with no edit | 1 | 1 | 4 | 1 |
| session timeouts | 2 | 2 | 4 | **1** |
| exact repeat calls | 61 | 76 | 94 | **51** |
| repeat searches of a term that already came back empty | 33 | 24 | 19 | **12** |
| median call of first edit | 17 | 23 | 23 | **16** |
| malformed-call errors ("mandatory input parameters are not present") | 11 | 0 | 41 | **0** |
| agent time | 116 min | 123 min | 151 min | **112 min** |

v5.0n = v4.8 + corrected empty-search rule (both output forms) + grep instead of paging through files + make the issue's
example work before docstrings/overloads + fix sibling functions that share the changed code + "a missing-parameter
error means the call was malformed: never resend it, use /tmp/fix.py".

- fastapi_12942: the patch matches the reference fix (handle `Annotated` in `_compat.field_annotation_is_complex`),
  found by call 16 with 29 calls; earlier versions guessed function names and re-searched them up to 19 times.
- rich_3480 is still unsolved: the agent fixed `Text.append` but not `append_text`; it grepped `append` with `-l`
  (file names only), so the sibling rule did not surface the twin method.
- One llama-server OOM kill (23:39) happened during rich_3480's hidden-test run: the unfixed `append_text` loops
  forever and grew host memory to 27.8 GB, so the kernel killed the biggest process. That explains the occasional
  server kills (the scorer's 4 GiB sandbox limit contains it). rich_3052 started during the 2-min restart; it has
  never been solved.

Decision: day 11 (2026-10-05) = v5.0n at 4.5 min / 40 calls (same budget as day 10, so days 10-11 compare prompts);
day 12 = v5.0n at 5.0 min / 50 calls (days 11-12 compare budgets).
