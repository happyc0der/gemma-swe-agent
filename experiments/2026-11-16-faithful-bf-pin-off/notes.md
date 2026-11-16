# T4 v34 (pushed 11-15 14:03 UTC, 8.48 GPU h): bf-pin-off vs pub-budget-fit-off on AB (thinking off)

| run (thinking off, official Evaluator) | solved | agent time | exact repeat calls | session timeouts | no-edit tasks | median first edit |
|---|---|---|---|---|---|---|
| **bf-pin-off AB** | **5/33** | 278 min | 513 of 1078 (48%) | 3 | 6 | call 14 |
| pub-budget-fit-off AB (paired) | 8/33 | 194 min | 444 of 1000 (44%) | 0 | 8 | call 17 |
| pub-budget-fit-off AB (earlier: v23, v29) | 9, 12 | ~216 min | ~30% | | | |

(scripts/faithful_metrics.py on data/faithful_results/bf-pin-off-AB/x/*; canary resolved 1/1.)

Reading:
- bf-pin-off lost fastapi_13537, fastapi_14458, requests_6644, rich_3894 (all solved by the paired base) and gained
  only fastapi_14360. Five tasks ran to 74-80 calls (base: three) and three hit the session timeout.
- 5/33 is the lowest thinking-off AB count of any budget-fit variant, and agent time is +43%. A single 33-task run
  moves by ~3 with identical files, so 5 vs 8 alone is weak, but the pre-registered rule was "pull if <= 7 thinking
  off", and slower sessions are exactly what pushes the 8-minute family toward the 12 h cap.
- The compaction correlation that motivated bf-pin (2+ compactions: 2/18 resolved) is probably hardness, not a
  lost task statement: hard tasks run long, and long runs compact.

Decision (11-16): bf-pin's LB days (11-21, 11-25, 11-27) removed before any LB run. A thinking-on pair goes on the
TPU lane (v9) for the record; it would need >= 3 tasks over the base on both sets to reopen the question.
