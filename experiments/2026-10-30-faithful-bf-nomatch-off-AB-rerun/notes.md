# bf-nomatch-off on AB, rerun (T4 kernel v31)

Kernel v31 (pushed 10-30 00:25 UTC, ran 00:43-04:26 UTC, ~4 GPU h): bf-nomatch-off on subset AB (33 holdout tasks),
identical files to kernel v26. It balances the paired design: base-off and bf-nomatch-off now each have two AB runs
and one DEV run. Data: data/faithful_results/bf-nomatch-off-AB-rerun.

Result: **10/33** (v26: 11/33), agent time 223 min (v26: 167 min), 1 session timeout.

## Pooled thinking-off comparison (same 66 tasks, 99 task-runs per config)

| config | AB run 1 | AB run 2 | DEV | pooled | agent time per run (min) | exact repeated calls | dead-term repeats | no-edit tasks |
|---|---|---|---|---|---|---|---|---|
| pub-budget-fit-off (base) | 9 | 12 | 9 | **30/99** | 220, 212, 242 (mean 225) | 1014/2683 (37.8%) | 54 | 17 |
| bf-nomatch-off | 11 | 10 | 10 | **31/99** | 167, 223, 200 (mean 197) | 919/2634 (34.9%) | 29 | 23 |

- Score: level (+1 task in 99 task-runs; one 33-task run alone moves by ~3 with identical files).
- Mechanism: the bullet halves the repeated dead-end greps (54 -> 29) and trims exact repeats a little, but more tasks
  end without any edit (17 -> 23).
- Speed: 12% less agent time on average (the first run's -22% was partly noise).

## Decision

Offline it neither helps nor hurts the score; it is somewhat faster, which matters only for the 12 h cap the base already
fits. The verdict rests on its LB days: day 1 = 8, day 2 submitted 10-30 02:35 UTC, day 3 after a base day. Promote only
if its LB mean over >= 3 days beats the base (9.5 over 6) by >= 1.5. No more GPU on it.

Next T4 screen (week from 10-31): bf-t10-off, the base-off with Gemma's recommended sampling (temperature 1.0, top_p 0.95,
top_k 64). The base-off repeats ~38% of its calls verbatim at temperature 0.2; sampling is a larger change than one
prompt bullet. AB first; DEV only if AB is not a clear regression (<= 7/33).
