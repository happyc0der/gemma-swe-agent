# Final submission selection (FINAL, 2026-11-27; one swap rule below for runs still scoring)

Keshav selects two submissions on the competition's Submissions page before **2026-12-02 23:59 UTC**.
The final score is the better private score of the two picks. A run's private half is close to a fresh draw from
its config's true mean (run-level effects such as a slow scoring machine hit both halves), so: pick the config with
the highest posterior mean, then its two completed runs with the highest public scores.

## Config means (public LB, k/58 truncated)
| config | our completed LB draws | our mean | other evidence |
| --- | --- | --- | --- |
| pub-budget-fit (base) | 10, 9, 8, 9, 11, 10, 11, 9, 10, 10, 9, 8 (1 unhandled error, 10-22) | 9.50 / 12 | 12 public draws of byte-identical files, 10.25 -> pooled **9.88 / 24** |
| bf-think1k | 12, 9, 10, 8, 10, 9, 8, 6 (finished) | 9.00 / 8 | none (thinking budget is not screenable offline) |
| bf-think2k | 10, 10, 9 | 9.67 / 3 | - |
| bf-t10 | 8, 10, 9 | 9.0 / 3 | thinking-on TPU AB 14 vs 13 |
| others (bf-nomatch, bf-lean, bf-think1k-lean, bf-think512) | 1-2 draws each | 7.0-8.0 | dropped |

No candidate beat the base by the +1.5 promotion margin; the only one that was ever ahead (think1k, 10.33 after 3)
regressed to 9.00 over 8. bf-think2k's 9.67 over 3 is level with the base and measured on 3 draws vs 24. The base is
the best-measured config and has the highest pooled mean.

## Recommendation
Select these two **pub-budget-fit** submissions (both 0.18 = 11/58, the base's highest public scores):

1. **2026-10-26 00:05 UTC** submission (description starts "day31: budget-fit reference bundle"; public score 0.18)
2. **2026-10-31 05:05 UTC** submission (description starts "fallback: budget-fit reference bundle"; public score 0.18)

Swap rule: base runs submitted 11-27 13:35 UTC and later are still scoring. If one of them completes with **0.20 or
more (>= 12/58)** before the deadline, it replaces the 10-26 pick. A run that is still pending at selection time
must not be picked. Not recommended: the bf-think1k 11-08 run (0.20 = 12/58, our highest single public score),
because its config mean is lower (9.00 vs 9.88); a 12 inside a config with SD ~1.6 is mostly draw noise.

Remaining LB slots all go to the base (fallback). Runs take ~31 h to score, so after the 11-27 run (scores ~11-28
evening UTC) about two more can complete (~11-30 and ~12-01 UTC); anything submitted after ~12-01 12:00 UTC may still
be pending at the deadline. Candidate freeze since 11-26: no new configs.
