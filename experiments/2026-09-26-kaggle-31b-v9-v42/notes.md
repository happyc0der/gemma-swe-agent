# Kaggle T4x2, real 31B (llama.cpp Q4_0, 32k context), prompt v4.2, 5.5 min / 30 calls: 2/33

Kernel `dankaxon/gemma4-31b-holdout-eval` v9, 210 min, one server restart (SIGKILL at 09:04 UTC).
Resolved: requests_7309, requests_6644. Every task ended on the 5.5 min budget (18 exhausted, 15 mid-turn)
at ~12 tok/s; mean 14.5 tool calls. On the T4 pair the time budget, not the prompt, is the binding
constraint, so v9 (2/33) vs v8 day-3 config (3/33) is noise. The 32k context removed the six
"exceeds the available context size" failures of v8. The scorer's 4x L4 with TP=4 is several times faster,
so these T4 runs only bound the prompt from below.
