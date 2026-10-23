# Faithful eval: bf-warn-off (budget-fit base + budget-warning bullet, thinking OFF) on set AB, kernel v24

Kernel v24, pushed 10-22 13:06 UTC, RUN_DONE 17:36 UTC (4.50 GPU h; agent time 234 min). Harness swegemma 0.2.11
(wheelhouse of 2026-10-12), llama.cpp pinned, canary passed (fastapi_14303 solved at 6 calls). One llama-server
restart (watchdog, host RAM, 16:52 UTC). Raw results: `data/faithful_results/bf-warn-off-AB/`.

Purpose: the paired thinking-off screen of candidate 1 (`experiments/variants/bf-warn` = pub-budget-fit + one
~70-token budget-warning bullet) against the base's own thinking-off twin (kernel v23, pub-budget-fit-off = 9/33).

## Result

| | pub-budget-fit-off (v23) | bf-warn-off (v24) |
|---|---|---|
| solved, 33 tasks | 9/33 | **10/33** |
| solved set | fastapi 13537 14301 14303 14458 15589; requests 6644 7205 7309; rich 3894 | fastapi 13537 14301 14303 14360 14458; requests 6644 7205 7309 7427; rich 3894 |
| gains / losses | | + fastapi_14360, + requests_7427; - fastapi_15589 |
| no-edit tasks | 6 | 3 |
| exact repeat calls | 281 of 818 (34%) | 389 of 962 (40%) |
| `edit_file` calls / missing `old_string` / exact repeats | 164 / 128 / 123 | **328 / 287 / 272** |
| tasks that hit the 80-turn cap | 2 (fastapi_5624, rich_3278) | **4** (fastapi_14583, fastapi_14964, rich_3052, rich_3278) |
| session timeouts | 1 | 0 |
| median first edit (call #) | 20 | 18 |
| agent time (run log / trace timestamps) | 220 / 155 min | 234 / 179 min |

### Did the bullet change behaviour at the warning?
- `budget_warning` appeared in 23 of 33 tasks in both runs (at call 18, i.e. 10 calls left), so the sample is paired.
- Next call after the first warning: base = read_file 8, run_command 15, edit_file 0; bf-warn = read_file 9,
  run_command 11, **edit_file 3**. The bullet's "your very next call must be the edit" was followed 3 times in 23.
- `submit_patch` after the warning: base 21 of 23, bf-warn 22 of 23. The base already submits after the warning
  almost every time, so the bullet's main intent (do not run out of calls without submitting) was already satisfied.
- Not one `edit_file` after the warning returned `status: ok` in either run (all post-warning edits were malformed).

### Side effect: more `edit_file` loops
- The bullet names `edit_file` as the call to make, and `edit_file` calls doubled (164 -> 328); 287 of them arrived
  without `old_string` (the backtick-malformed call) and 272 were exact repeats. Four tasks burned all 80 turns on
  that loop (11-22 min each at the scaled cap) against two in the base. Malformed calls do not count against the
  28-call cap, so nothing stops the loop except the turn cap or the clock.

## Verdict
- +1 task is inside the identical-file noise (pooled LB SD 1.56 tasks; offline AB runs of one config differ by
  about the same), the intended mechanism was already present in the base, and the measurable side effect is more
  looping and more agent time: for the 8-min family the clock (12 h cap) is the binding risk, so a change that
  trends toward more turns is the wrong direction even if the score is flat.
- Caveat: thinking OFF. The LB base runs thinking ON, where malformed `edit_file` calls may be rarer; but the LB
  evidence we would buy (>= 3 LB days) is better spent on a candidate that targets the loop itself.
- **Decision (10-23): bf-warn is withdrawn from the LB queue (0 LB days used)**; its 10-24 queue file is removed and
  the base runs instead. Candidate 2 `bf-editfb` (edit_file error -> one run_command fix script; the loop is the
  dominant failure in both screens) takes the next candidate slot: kernel v25 = bf-editfb-off after the quota reset
  (10-24), LB day queued for 10-26 so the 10-25 run can withdraw it if the screen is bad.
