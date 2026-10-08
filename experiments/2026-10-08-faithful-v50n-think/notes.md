# Faithful eval: v5.0n with thinking on vs off (same 16 holdout tasks)

Kernel `dankaxon/gemma4-faithful-eval` v7, T4x2, 03:53-07:12 UTC (162 min of agent runs, 3.3 GPU h).
Same prompt and budget as v5.0n (3.5 min x3, 40 calls); sampling adds `include_thoughts: true`, `thinking_budget: 2048`,
`max_output_tokens: 8192`. Startup check confirmed per-request thinking turns on (458 reasoning chars for "17 * 23").

| metric | thinking off (v5.0n) | thinking on |
|---|---|---|
| solved | **9** | 6 (lost fastapi_12942, fastapi_14360, requests_6644; gained none) |
| session timeouts | 1 | **9** |
| calls per task | ~28 | ~21 |
| exact repeat calls | 51 | **18** |
| median call of first edit | 16 | **11** |
| output tokens per step | median ~35 | median 97, p90 584, max 2211 |
| agent time | 112 min | 162 min |

Verdict: thinking removes most loops and gets to an edit sooner, but the reasoning tokens cost so much time that 9 of
16 tasks hit the session timeout; at a scorer-feasible budget (4.5 min, 120 tasks in 12 h) it loses. Not submitted.
