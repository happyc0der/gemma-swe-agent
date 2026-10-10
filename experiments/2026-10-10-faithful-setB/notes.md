# Faithful eval on set B (17 stable holdout tasks never used for tuning): v5.0n vs v5.2

Kernel v12, 10-10 01:09-05:35 UTC (4.4 GPU h). First run under the **new harness** (swegemma 0.2.11 / adk_submission
0.2.13, wheelhouse of 2026-10-09), llama.cpp pinned to 71ad0590f, canary passed (fastapi_14303 solved, median 35
output tokens/step), thinking verified off (`thinking_level: none`).

| | v5.0n | v5.2 |
|---|---|---|
| set B solved | **4/17** (fastapi_14458, 14485, rich_3777, 3894) | 2/17 (fastapi_15589, rich_3894) |
| set A solved (16 tasks, old harness) | 9 | 8 |
| **all 33** | **13** | 10 |
| set B repeat searches of empty terms | 33 | 18 |
| set B paging (>=4 chunk reads) | 5 tasks | 1 task |
| set B median first edit | call 24 | call 31 |

Verdict: v5.0n stays the daily submission. v5.2's rules remove the failures they target (empty-term re-searches and
paging down, 0 malformed edits on set A) but do not raise the solve rate; set B also confirms the holdout is much
harder than set A (4/17 vs 9/16 for the same prompt), so set A alone overstated our level.
