# Faithful eval: the budget-fit base prompt with thinking OFF (pub-budget-fit-off) on set AB, kernel v23

Kernel v23, pushed 10-21 13:13 UTC, RUN_DONE 17:28 UTC (4.28 GPU h; agent time 220 min). Harness swegemma 0.2.11
(wheelhouse of 2026-10-12), llama.cpp pinned, canary passed (fastapi_14303 solved at 6 calls). One llama-server
restart (watchdog, host RAM). Raw results: `data/faithful_results/bf-off-AB/`.

Purpose: a thinking-off screen of the official starter prompt as used by the daily LB base (pub-budget-fit, which
runs with thinking 4096 ON and cannot be evaluated on T4s), to get a paired baseline for single-bullet candidates
(bf-warn-off = kernel v24, bf-editfb-off = kernel v25).

## Result vs our v5.8 (kernel v19, the conservative fallback)

| | v5.8 (v19) | pub-budget-fit-off (v23) |
|---|---|---|
| solved, 33 tasks | **14/33** | **9/33** |
| solved set | fastapi 12942 13537 14301 14303 14360 14458 14485 15589 5624; requests 6644 7309 7427; rich 3777 3894 | fastapi 13537 14301 14303 14458 15589; requests 6644 7205 7309; rich 3894 |
| no-edit tasks | 3 | 6 |
| exact repeat calls | 128 of 935 (14%) | **281 of 818 (34%)** |
| repeat searches of a dead term | 17 | 38 |
| session timeouts | 5 | 1 (24 min scaled cap; the 80-turn cap hit twice) |
| median first edit (call #) | 15 | 20 |
| agent time | 228 min | 220 min |

### The loop: `edit_file` without `old_string`
- 164 `edit_file` calls; **128 returned the harness error "mandatory input parameters are not present: old_string"**
  (the call reaches the harness without its `old_string` argument); 24 returned `status: ok`; 3 a file error.
- 125 of the 164 were exact repeats. rich_3278 (71 repeats) and fastapi_5624 (53) ran to the 80-turn cap on this
  loop alone; malformed calls do not count against the 28-call cap, so nothing stopped them. Also fastapi_13713
  (23), rich_3480 (19), fastapi_14482 (16), rich_3942 (15).
- v5.8 avoids this by construction (no `edit_file` tool; edits through one `run_command` fix script).

### Reading
- With thinking off, the starter prompt is 5 tasks below our v5.8 on the same 33 tasks, and the gap is mostly the
  edit loop plus "no edit" tasks. On the LB the same files with thinking ON average 10.00/58 (10 public draws +
  our day 26 = 10), well above our thinking-off configs (~6-7), so thinking is doing work this screen cannot see.
- The screen is still useful as a paired baseline: a bullet that helps here on the same tasks is a reasonable bet
  for the thinking-on LB variant, and it costs no LB day.
- Candidate from this result: `experiments/variants/bf-editfb` (one bullet: on an `edit_file` error, make the edit
  with one `run_command` Python script, never retry the same call), thinking-off twin `bf-editfb-off` for kernel v25.
