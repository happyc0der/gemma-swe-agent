# MSI proxy: prompt v3, Gemma 4 12B in Ollama (32k ctx, thinking off), 33 usable holdout tasks, 10 min / 40 calls / 80 turns, concurrency 2

Result: **1/33 (3%)**, but the run is NOT a valid prompt baseline.
Taxonomy (swelite analyze): budget 21, loop 9, broke_tests 2, resolved 1 (requests_7205).

Diagnosis from traces:
- Ollama's OpenAI endpoint ignored `max_tokens` (2048): fastapi_14583 generated 22,663 tokens in one response containing 667 tool calls (630 rejected as over budget), filling the 32k context. Other tasks show single responses of 5-20k tokens.
- With OLLAMA_NUM_PARALLEL=2 and concurrency 2, a runaway generation in one slot starved the other: 21 "budget" tasks made 1-4 tool calls in the first seconds and then waited ~10 min on a model call that never returned before the session cap.
- Repetition loops (9) and escaped-anchor edit failures persist from the 4-task batches.

Decisions:
1. Ollama is retired as the iteration proxy; `serve/Modelfile.gemma4-12b-32k` now sets `num_predict 2048` if it is ever used again.
2. vLLM (installed on the MSI, honors max_tokens and thinking_budget, same gemma4 parsers as the competition harness) becomes the proxy. First run: the day-2 submission config (thinking medium/2048) on the same 33 tasks via `serve/run_vllm_holdout.sh`.
3. Harness note: a single model response can carry hundreds of function calls; the tool budget gate handles it (rejections don't count), but the time budget is what ends such a task. The official harness behaves the same.
