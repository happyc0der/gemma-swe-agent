# TPU v6 (pushed 11-07 ~14:10 UTC, queued ~63 h, ran ~05:25-11:57 UTC 11-10, 6.51 TPU h): first full thinking-on offline runs

The litellm==1.104.2 pin fixed v5's canary failure. Everything ran: weights in /dev/shm in 54 s, vLLM
serving after 585 s, decode 64.1 tok/s -> time_scale 0.51 (8 min on the scorer = 4.08 min here), canary
fastapi_14303 resolved 1/1 in 90 s (13 steps), stage 2 rc=0. The fourth run (bf-t10 DEV) was skipped by
the session-budget rule (a run starts only before 5.5 h); three ~2 h runs fit one session.

| run (thinking on, official Evaluator) | solved | agent time | exact repeat calls | session timeouts | median first edit |
|---|---|---|---|---|---|
| pub-budget-fit AB | 13/33 | 117 min | 180 of 841 (21%) | 0 | call 8 |
| bf-t10 AB | 14/33 | 127 min | 75 of 732 (10%) | 2 | call 10 |
| pub-budget-fit DEV | 13/33 | 123 min | 149 of 888 (17%) | 4 | call 12 |

(scripts/faithful_metrics.py on data/tpu_results/v6/x/*; raw files in data/tpu_results/v6.)

Reading:
- The base solves 13/33 with thinking on, on both sets, against 9-12/33 for its thinking-off twin on
  the T4 lane. No task ended without a source edit (thinking-off: 6-10 per run). Lane counts are not LB
  counts: thinking_token_budget is still ignored here (budget 64 -> 542 reasoning tokens), and the
  hidden tasks differ.
- bf-t10 vs base on AB: 14 vs 13, i.e. level (one 33-task run moves by ~3 with identical files). Task
  flips: t10 gained fastapi_14791 and fastapi_15589, lost fastapi_14485 and rich_3278. Temperature 1.0
  halves the verbatim repeats, as it did thinking-off, but costs 9% more agent time and two session
  timeouts. Consistent with its LB draws (8, 10 vs base mean 9.67): no sign of a gain, a small runtime
  cost. LB day 3 (11-11) stays queued to finish the 3-run verdict.
- Runtime projection is relative only: 117-123 min of scaled agent time per 33 tasks for the base.
  A candidate that needs clearly more than that is a 12 h risk.

Next (v7, pushed 11-10): bf-lean AB, bf-lean DEV (pairs with base 13 and 13), bf-t10 DEV; a base AB
rerun is listed fourth and will be skipped unless the runs are shorter. Collect to data/tpu_results/v7.
The thinking-budget candidates (think1k, think512) cannot be screened on this lane.
