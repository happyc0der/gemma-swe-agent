# TPU v7 (pushed 11-10 ~14:20 UTC, queued ~55 h, ran ~21:30 UTC 11-12 to 04:01 UTC 11-13, 6.62 TPU h): bf-lean and bf-t10 thinking on

Same lane as v6 (vllm-tpu 0.32.0, weights in /dev/shm in 58 s, decode 64.1 tok/s -> time_scale 0.51, stage 2 rc=0).
Three runs fit the session; the fourth (base AB rerun) was skipped by the session-budget rule.

| run (thinking on, official Evaluator) | solved | agent time | exact repeat calls | session timeouts | median first edit |
|---|---|---|---|---|---|
| pub-budget-fit AB (v6) | 13/33 | 117 min | 180 of 841 (21%) | 0 | call 8 |
| **bf-lean AB** | **17/33** | 124 min | 146 of 786 (19%) | 0 | call 9 |
| bf-t10 AB (v6) | 14/33 | 127 min | 75 of 732 (10%) | 2 | call 10 |
| pub-budget-fit DEV (v6) | 13/33 | 123 min | 149 of 888 (17%) | 4 | call 12 |
| **bf-lean DEV** | **14/33** | 124 min | 228 of 880 (26%) | 3 | call 8 |
| bf-t10 DEV | 15/33 | 121 min | 76 of 774 (10%) | 4 | call 11 |

(scripts/faithful_metrics.py on data/tpu_results/v6/x/* and data/tpu_results/v7/x/*; raw files in data/tpu_results/v7.)

Reading:
- bf-lean 31/66 vs base 26/66. On AB it kept all 13 base solves and added fastapi_12942, fastapi_14791,
  rich_3777, rich_4075; on DEV it gained fastapi_11194, fastapi_13207, fastapi_14459 and lost httpx_3672,
  rich_3470. One 33-task run moves by ~3 with identical files, so +5 over two runs is suggestive, not
  proof; it clears the "pull if <= 9" rule by a wide margin. Agent time 124 vs 117-123 min: no
  runtime advantage on this lane, no clear cost either.
- bf-t10 29/66 vs base 26/66 offline, but its LB verdict is in (8, 10, 9 = 9.0 over 3, below the base);
  the lane's +3 did not show on the LB. That is the caution for bf-lean too: only LB days decide.
- Lane counts are not LB counts (thinking_token_budget is ignored here; hidden tasks differ).

Decisions (11-13):
- bf-lean LB days moved forward: 11-14, 11-18, 11-22 (were 11-16, 11-20, 11-24). bf-think512 moves to
  11-16, 11-20, 11-24.
- bf-think1k-lean (built 11-08, unqueued because think1k's mean was base + 0.67 < + 1.0) is now queued
  for 11-15, 11-19, 11-23 on the new bf-lean evidence: it stacks the two changes with a positive sign
  (think1k LB + 0.67, lean offline + 5/66), and the base's mean is already measured over 19 pooled draws.
  The base runs again 11-25 and in the final week.
- v8 (pushed 11-13 14:03 UTC, commit ec2aab9): base AB, bf-lean AB, base DEV reruns (bf-lean DEV fourth,
  likely skipped) to pool a second pair. Collect to data/tpu_results/v8.
