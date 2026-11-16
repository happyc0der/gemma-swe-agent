# TPU v8 (pushed 11-13 14:03 UTC, queued ~50 h, 6.56 TPU h): base and bf-lean thinking-on reruns

Same lane as v6/v7 (weights in /dev/shm in 52 s, decode 64.1 tok/s -> time_scale 0.51, canary 1/1, stage 2 rc=0).
Three runs fit; bf-lean DEV was skipped by the session-budget rule.

| run (thinking on) | solved | agent time | exact repeat calls | session timeouts |
|---|---|---|---|---|
| pub-budget-fit AB | 13/33 | 122 min | 255 of 935 (27%) | 1 |
| bf-lean AB | 14/33 | 121 min | 268 of 927 (29%) | 2 |
| pub-budget-fit DEV | 15/33 | 129 min | 103 of 760 (14%) | 4 |

Pooled with v6/v7: base AB 13, 13 and DEV 13, 15 = 54/132 (13.5 per run); bf-lean AB 17, 14 and DEV 14 = 45/99
(15.0 per run). The +5 over two runs seen in v7 shrinks to +1.5 per run, inside one run's noise (~3).

LB: bf-lean day 1 = 8, bf-think1k-lean day 1 = 7 (base 9.70 over 10). Promotion needs a 3-day mean >= 11.2, i.e.
26 and 27 from the two remaining days; neither is reachable (our best single draw of any config is 12). Both
dropped on 11-16; their slots go to bf-think1k, the one config above the base.
