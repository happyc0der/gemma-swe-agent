# Final submission selection (DRAFT 2026-11-25; final version due 2026-11-29)

Keshav selects two submissions on the competition's Submissions page before **2026-12-02 23:59 UTC**.
The final score is the better private score of the two picks. A run's private half is close to a fresh draw from
its config's true mean (run-level effects such as a slow scoring machine hit both halves), so: pick the config with
the highest posterior mean, then its two completed runs with the highest public scores.

## Config means (public LB, k/58 truncated)
| config | our completed LB draws | our mean | other evidence |
| --- | --- | --- | --- |
| pub-budget-fit (base) | 10, 9, 8, 9, 11, 10, 11, 9, 10, 10, 9 (1 unhandled error, 10-22) | 9.64 / 11 | 12 public draws of byte-identical files, 10.25 -> pooled **9.96 / 23** |
| bf-think1k | 12, 9, 10, 8, 10, 9, 8 (day 8 pending) | 9.43 / 7 | none (thinking budget is not screenable offline) |
| bf-think2k | 3 draws | 9.67 / 3 | - |
| bf-t10 | 8, 10, 9 | 9.0 / 3 | thinking-on TPU AB 14 vs 13 |
| others (bf-nomatch, bf-lean, bf-think1k-lean, bf-think512) | 1-2 draws each | 7.0-8.0 | dropped |

No candidate beat the base by the +1.5 promotion margin; the only one that was ever ahead (think1k, 10.33 after 3)
regressed to 9.43 over 7. The base is the best-measured config and has the highest pooled mean.

## Recommendation (draft)
Pick two **pub-budget-fit** runs with the highest public score: currently the **2026-10-26** and **2026-10-31**
submissions (both 0.18 = 11/58). If a base run from 11-25 to 11-30 scores 12 or more, it replaces the older of the
two. Not recommended: the bf-think1k 11-08 run (0.20 = 12/58, our highest single public score) because its config
mean is lower (9.43 vs 9.96); a 12 inside a config with SD ~1.6 is mostly draw noise.

Remaining LB slots (11-25 to 12-01) all go to the base (fallback), adding candidates for the picks. Day 8 of
think1k (pending) is recorded but cannot change the config choice (even 12 gives 9.75 / 8).
