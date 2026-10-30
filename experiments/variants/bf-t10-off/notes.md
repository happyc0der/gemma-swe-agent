# bf-t10-off

Thinking-off screen of bf-t10: pub-budget-fit-off with Gemma's recommended sampling (temperature 1.0, top_p 0.95,
top_k 64) instead of temperature 0.2. Offline-eval screen only (T4 faithful eval); never submitted.

Why: the thinking-off base repeats itself verbatim a lot at 0.2 (exact repeated calls: 281/818, 217/807 and 516/1058
over its three runs), and our older thinking-off traces lost such loops at 0.7. Compare against the three base-off
runs (AB 9 and 12, DEV 9; pooled 30/99) on solved tasks, exact repeats, no-edit tasks and agent time.
