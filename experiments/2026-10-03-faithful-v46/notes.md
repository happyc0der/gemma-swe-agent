# Faithful eval: prompt v4.6 vs v4.5, same 16 holdout tasks

Kernel `dankaxon/gemma4-faithful-eval` v2 (T4x2, 2.4 h). Same setup as v1 (official Evaluator, scorer-like
sandbox, real 31B with thinking off, 10.5 min = 3.5 x3, 40 calls). Only the variant changed.

| metric | v4.5 (temp 0.2) | v4.6 (temp 0.7) |
|---|---|---|
| solved | 7/16 | **8/16** |
| tasks with >= 5 identical calls in a row | 3 | **0** |
| exact duplicate calls (all tasks) | 142 | **57** |
| tasks with no edit at all | 5 | **3** |
| median call of first edit | 33 | **18** |
| total tool calls | 491 | 441 |
| eval wall time | 137 min | 110 min |

Flips: fastapi_14301 and rich_3278 (the two worst loopers under v4.5, 23 and 19 repeats) are solved under v4.6;
requests_7427 went from solved to failed in only 12 calls (sampling variance). The net +1 is inside the noise of
16 tasks; the mechanism (no loops, earlier edits) is what the leaderboard could not show.

Memory: llama-server's RSS grows to ~31 of 32 GB within ~10 min of each start (weights copied to host RAM with
mmap disabled, plus the default 8 GB host prompt cache), then it is OOM-killed (3 times in this run). Next runs use
`--cache-ram 0` and default mmap (full GPU offload, so the host copy is reclaimable page cache).

Decision: day 10 (2026-10-04) submits v4.6 at 3.5 min (day 9 at 3.5 min finished within ~7 h).
