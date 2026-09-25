# Kaggle submissions (1/day)

| date (UTC) | config snapshot | change vs previous | public score | notes |
|---|---|---|---|---|
| 2026-09-24 ~07:45 | experiments/2026-09-24-day1-sample-prompt | first submission: sample prompt, no adapters, 8 min / 40 calls / 80 turns | **0.00** | mechanics work (COMPLETE); sample prompt does not submit patches. LB top 0.12 |
| 2026-09-25 00:05 | submission/ @ d60350c | day2: prompt v3 (task in system prompt, strict protocol), thinking medium/2048, 10min/50calls/100turns | **0.00** | COMPLETE. Same config solved 6/33 on the 12B vLLM proxy. Hypothesis: 12 h global cap with sequential execution (sample eval_config uses 1 min/task); 120 x 10 min = 20 h |
