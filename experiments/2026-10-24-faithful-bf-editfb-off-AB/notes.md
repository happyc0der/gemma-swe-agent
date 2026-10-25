# Faithful eval: bf-editfb-off (budget-fit base + edit_file-error fallback bullet, thinking OFF) on set AB, kernel v25

Kernel v25, pushed 10-24 13:22 UTC, RUN_DONE 17:46 UTC (4.40 GPU h; agent time 228 min). Harness swegemma 0.2.11
(wheelhouse of 2026-10-12), llama.cpp pinned, canary passed. One llama-server restart (watchdog rc=-9, host RAM,
17:01 UTC). Raw results: `data/faithful_results/bf-editfb-off-AB/` (collected 10-25).

Purpose: the paired thinking-off screen of candidate 2 (`experiments/variants/bf-editfb` = pub-budget-fit + one
~75-token bullet: "if edit_file errors, make the edit with one run_command Python script; never retry the same call").

## Result

| | pub-budget-fit-off (v23) | bf-warn-off (v24) | bf-editfb-off (v25) |
|---|---|---|---|
| solved, 33 tasks | 9/33 | 10/33 | **7/33** |
| no-edit tasks | 6 | 3 | **10** |
| exact repeat calls | 281 of 818 | 389 of 962 | 347 of 960 |
| `edit_file` calls / errored / missing `old_string` | 164 / 135 / 128 | 328 / 292 / 287 | 259 / 236 / 229 |
| Python `run_command` right after an `edit_file` error | 2 (2 tasks) | 1 (1 task) | **6 (2 tasks)** |
| tasks at the 80-turn cap | 2 | 4 | 3 (fastapi_14964, requests_6644, rich_3278) |
| median first edit (call #) | 20 | 18 | 23 |

Solved set: fastapi 13537 14301 14303 14360; requests 7205 7309; rich 3894. Versus the base twin: + fastapi_14360;
- fastapi_14458, fastapi_15589, requests_6644 (requests_6644 fell into an 80-turn edit_file loop).

## Reading
- The bullet was ignored: after 236 erroring `edit_file` calls the model switched to a Python fix script 6 times, in
  2 tasks. The malformed-call loop (missing `old_string`) still dominates and does not count against the 28-call cap.
- Three one-bullet additions to the budget-fit prompt (bf-warn, bf-editfb, and the base) now span 7-10 of 33 on the
  same tasks; with no measurable compliance, the differences are noise or mild harm. Prompt bullets appended to the
  official starter prompt do not change this model's tool-call habits in thinking-off mode.
- Decision: **bf-editfb withdrawn** before its LB day (`.submit_queue/2026-10-26-bf-editfb` deleted 10-25).
  Next screen: bf-nomatch-off (kernel v26). If it also shows no compliance, stop prompt-bullet candidates for the
  budget-fit base and keep the base for the remaining LB days.
