# MSI vLLM proxy: day-2 submission config on the 33 usable holdout tasks

Model: Gemma 4 12B W4A16 in vLLM 0.30 (gemma4 tool/reasoning parsers, compiled mode, ~34 tok/s), concurrency 2.
Config: prompt v3, temperature 0.2, top_p 0.95, max_output_tokens 4096 (8192 for the first 4 tasks before the pre-submission change), thinking_config medium/2048 (not applied: ADK's LiteLlm does not map it for vLLM, so this is effectively thinking-off), 10 min / 50 calls / 100 turns.

Result: **6/33 resolved (18.2%)** vs 1/33 for the same prompt on Ollama (invalid run) and 0/4 on the Mac proxy.
Resolved: requests_7309, requests_6644, fastapi_14458, fastapi_14301, fastapi_14303, fastapi_13537.
Taxonomy: loop 15, no_patch 7, broke_tests 4, edit_mismatch 1, resolved 6. Mean per task: 30.9 calls, 13.5 identical repeats, 1.0 successful edits, 23.9 run_command, 5.2 read_file, 0.0 graph-tool calls.

Reading:
- Identical-call loops are the dominant failure (45% of tasks). Temperature 0.2 makes the model deterministic given identical context, so a failed call is retried verbatim. The prompt's loop-escape rule does not overcome it.
- no_patch (7): exploration without ever editing, several ending early (50-80 s) on text-only turns.
- broke_tests (4): plausible partial fixes; the earlier "run the tests that reference the function" rule is not consistently followed.
- The graph tools are never used.
- One task hit the 32k window with the 8192 cap (fixed to 4096 before the day-2 submission).

Next experiment (launched right after): same 33 tasks, temperature 0.7 (model card default range), everything else equal.

## Re-analysis (context overflow)
With the analyzer's new `context_overflow` buckets: **21 of 32 tasks ended in `ContextWindowExceededError`** (some after only 12-14 calls), most while looping. Prompt growth is ~630 tokens per LLM call (p90 1,135) from a 4.3k start; ADK never compacts inside a task (see docs/competition.md). This, not the tool-call budget, is the binding constraint. Prompt v4 adds explicit context-budget rules (bounded outputs, ~20-call plan) and the sampling cap drops to 2048 to widen the usable window.
