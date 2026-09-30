# What the public notebooks do (read 2026-09-29)

Configs pulled with `kaggle kernels pull` into `kaggle/reference/`. Scores are the authors' own claims.

| notebook | claimed LB | sampling | budget per task | structure |
|---|---|---|---|---|
| lucifer19/black-cat-swe-agent-pack-instinct | 0.10 (0.08 single-agent fallback) | temp 0.2, top_p 0.95, top_k 40, 4096 out, thinking off | 5 min, 48 calls, 100 turns, timeout 180 | coder + `second_opinion` advisor sub-agent (1536 out) |
| nihilisticneuralnet/0-10-gemma-4-developer-agent-submission | 0.10 | temp 0.15, 8192 out (2048 for sub-agents), thinking off | 4.5 min, 40 calls, 100 turns, timeout 60 | coder + `code_localizer` + `code_verifier` agent tools |
| zhukovoleksiy/gemma-4-walkthrough-first-submission | 0.10 (v2) | temp 0.2, top_k 40, 4096-8192 out, thinking off | 4 min, 80 turns, timeout 120 | coder + read-only `code_analyzer` |
| mizeroluckygall/pathfinder-gemma-4-agent-eda-baseline | 0.08 | temp 0.2, top_k 40, 8192 out, thinking off | none | coder + analyzer |
| romanrozen/gemma-eda-baseline-for-a-start-lb-top-1 | 0.12 (09-24) | temp 0.2, top_k 40, 8192 out, thinking off | none | coder + analyzer |
| **ours, day 5** | **0.10** | **temp 0.7**, 4096 out, thinking off | 4.5 min, 30 calls, 60 turns, timeout 180 | coder only |

Takeaways:
- Everyone at 0.08-0.12 uses temperature 0.15-0.2 with thinking off. Our 0.7 came from 12B-proxy loops, never
  tested on the 31B.
- Most use an analyzer-style AgentTool. Oleksii's notes: `skip_summarization: true` ends the coder's turn after
  every analyzer call and triggers a harness nudge; he switched to `skip_summarization: false` with a one-line
  request to the analyzer.
- Tool-call caps are 40-48 where set; ours is 30 and our prompt plans ~15 calls.
- Nobody public is above 0.12; the leaderboard top (0.13-0.15) is private.

Plan, one change per day on top of day 5 (0.10): day 7 temperature 0.2 + top_k 40; then a higher call cap with
a relaxed call plan; then an analyzer sub-agent with `skip_summarization: false`.

## Results so far (2026-09-30)
- Day 7, temperature 0.2 + top_k 40: **0.10**, the same as day 5 at temperature 0.7. Neither the budget above 4.5 min
  nor the temperature moves the score beyond the ~1-2 task noise band.
- Day 8 (2026-10-01): agents were ending early by choice (runs finish in ~6.5-7 h), so prompt v4.4 plans ~25 calls
  (was ~15), caps at 40 calls / 80 turns (was 30 / 60), and calls submit_patch as soon as the reproduction passes and
  again after later edits. In the official runner a context-overflow error skips the working-tree fallback and
  loses unsubmitted work, while submit_patch is free and does not end the session.
