# Day 2: prompt v3, medium thinking (budget 2048, max_output 8192), 10 min / 50 calls / 100 turns

Change vs day 1: prompt rewritten (task embedded via {problem_description} so it survives compaction; explicit locate/reproduce/fix/verify/submit protocol; heredoc reproduction; no verbatim retries; scripted edit fallback), thinking budget halved, output cap halved, per-task time 8 -> 10 min, tool calls 40 -> 50.
Hypothesis: day-1 zero came from never submitting a patch; the protocol plus task-in-system-prompt should produce patches on a meaningful fraction of tasks. Expect > 0.
Proxy evidence (Gemma 4 12B, Ollama, thinking off, Mac): v2 prompt ran tight loops (no nudges, explicit submit) but 0/4 resolved due to repetition loops and double-escaped edit anchors; v3 adds the loop-escape rules. Not validated on the 31B.

## Pre-submission change (2026-09-24 21:30 EDT)
max_output_tokens 8192 -> 4096. On the vLLM proxy a task hit `ContextWindowExceededError` (24.6k prompt + 8192 requested > 32768) and died; the competition's vLLM has the same 32k window. 4096 leaves room for prompts up to ~28k.
Observation: in swelite, ADK's LiteLlm does not translate `thinking_config` into a vLLM request, so proxy runs are effectively thinking-off; whether the organizers' adk-submission layer injects Gemma 4's thinking trigger is unknown. The config keeps thinking medium/2048 in case it does.
