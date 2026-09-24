# Day 1: organizers' sample prompt, no adapters, budgets 8 min / 40 calls / 80 turns

Hypothesis: the day-1 leaderboard zeros come from the sample eval_config (1 min / 10 calls). Same prompt with room to work should score > 0.
Purpose: learn the submission mechanics and get a first real number on the hidden set.
Model: gemma-4-31b-it-qat-w4a16-ct on the organizers' 4x L4 (via Kaggle submission).

## Result
Public score **0.00** (status COMPLETE). Proxy runs of the same prompt on Gemma 4 12B show the failure mode: 1-4 tool calls, then text-only turns and nudges until the budget ends; no submit_patch, empty diff. Two compounding causes seen locally: (1) the prompt never restates the task, so after ADK compaction the model asks "please provide the problem"; (2) long thinking + large max_output_tokens burns minutes per turn. Day 2 must ship prompt v1 (task embedded via {problem_description}, explicit submit protocol) with a tighter output cap.
