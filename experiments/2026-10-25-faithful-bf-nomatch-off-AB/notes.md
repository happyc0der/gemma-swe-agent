# Kernel v26: bf-nomatch-off on set AB (33 tasks) = 11/33

Pushed 2026-10-25 13:07 UTC, ran 3.34 h (RUN_DONE 167 min). Archive: data/faithful_results/bf-nomatch-off-AB
(results/faithful-bf-nomatch-off-setAB). Paired baseline: kernel v23 pub-budget-fit-off = 9/33.

| run | resolved | empty patches | no-match greps | exact repeats | agent min | 80-turn cap | 28-call cap |
|---|---|---|---|---|---|---|---|
| pub-budget-fit-off (v23) | 9 | 6 | 81 / 396 run_command | 30 | 219.9 | 2 | 0 |
| bf-nomatch-off (v26) | 11 | 8 | 85 / 401 | 20 | 166.9 | 2 | 2 |

- Gained fastapi_12942, fastapi_14360, fastapi_5624; lost fastapi_15589 (net +2; offline single runs move by about
  that much, so this is a screen, not a verdict).
- No-match greps are as frequent (the model still searches for absent text) but repeats fell by a third, and
  fastapi_14482, which repeated one grep to the call cap in v23, now produces a 699-byte patch (still unresolved).
- Agent time fell 53 min (-24%), so the bullet does not add runtime risk for the 8-min LB family.
- Two tasks (fastapi_14485, fastapi_14448) now end at the 28-call cap with empty patches.

Decision: first bullet candidate to beat its base twin without a runtime cost -> 3 LB days for bf-nomatch, interleaved
with base days (first: `.submit_queue/2026-10-27-bf-nomatch`, goes out 10-27 00:05 UTC).
