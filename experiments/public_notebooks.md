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

## 2026-10-11 (daily routine)
- `dmitriigluzdov/gemma-4-measure-before-you-tune` (63 votes, run 10-11): reports that the public **Budget-Fit single
  agent** bundle (`verracodeguacas/gemma-4-agent-budget-fit-single-agent`) reproduces **0.18** on the public LB (their
  submission 56932359), vs our 0.06-0.10. Config: one coder, **8 min / 28 tool calls / 80 turns, thinking budget 4,096
  ON**, command timeout 240 s. Same author saw one byte-identical archive score 0.10 and 0.06 on different days (LB
  noise ~0.06), and estimates 120 hidden tasks run sequentially in 12 h => ~282-350 s/task average, so long budgets only
  fit if most tasks end early. Our own "thinking on loses" result (6/16 vs 9/16) was at a 3.5-min (x3) budget where
  thinking caused session timeouts; an 8-min budget is untested here. Not adopted: needs Keshav's decision and an
  offline AB eval under the ship rule.

## 2026-10-12 (daily routine)
- `hitarthjain0/gemma-4-apex-silver-agent-lb-0-24` credits `honghanhhh/gemma-4-baseline-lb-0-24` with a **0.24** public
  score for a "contract-first" single agent on the Budget-Fit limits (8 min / 28 calls / 80 turns / 240 s, thinking
  budget 4096 ON, max_output_tokens 8192, temperature 0.2). Prompt ideas: copy the issue's exact names/strings/status
  codes before searching; one `git grep` then a <=120-line read; source edit by call 12; at most one focused check and
  one repair; scratch files in /tmp and test paths checked out before submit_patch; graph tools not registered. The
  notebook's own 0.24 is claimed, not shown. This is the same budget/thinking family as our pending day-17 LB test
  (`v50n-think8`), so that score decides whether this direction is worth an offline AB eval.

## 2026-10-15: contract-first bundle staged as a one-day LB test (Keshav's choice)
- Source: `honghanhhh/gemma-4-baseline-lb-0-24` ("v3 (0.22 config + targeted prompt edits)", based on the public
  `gemma-4-budget-aware-coding-agent-v2`, reported 0.22; the 0.24 title is claimed, not shown). Public Kaggle notebook,
  no explicit license (Kaggle's default for public code is Apache 2.0); used as-is for a test, credited here.
- Bundle copied byte-for-byte to `experiments/variants/pub-contract-first` (extracted from the notebook's embedded
  `FILES`): temperature 0.2, top_p 0.95, max_output_tokens 8192, thinking_budget 4096 + include_thoughts true, tools
  incl. read_file and the three graph tools (prompt forbids the graph tools), 8 min / 28 calls / 80 turns / 240 s.
- Prompt ideas vs ours: a hard call plan (edit by call 12, nothing new after call 20), "an unedited tree always
  scores zero", spec extraction before searching, batched git grep, at most 2 verify calls, every parallel
  implementation (sync/async, overloads, `__all__`), FastAPI `docs_src/` executable docs, never conclude no change.
- Compiles under the current harness (COMPILE_OK, enable_thinking true, thinking_token_budget 4096, 9 tools).
- Judge on the LB: if it reproduces >= 0.17 (10/58) the gap to our ~0.10 is prompt + config and we build on it
  (offline AB eval of our prompt in this style); if <= 0.12, the claim does not hold for us and v5.0n stays.
