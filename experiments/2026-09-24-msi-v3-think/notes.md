# MSI proxy: prompt v3, Gemma 4 12B in Ollama (32k ctx, 50 tok/s on the 3080 Ti), thinking ON, 4 tasks, 12 min / 40 calls

Result: 0/4, and not informative. Three tasks spent the entire budget inside one model call after 2-3 tool calls (the third call ran >11 min = tens of thousands of tokens), fastapi_11355 made 14 grep calls and never edited.
Cause: Ollama's Gemma 4 thinking channel is not bounded by max_tokens and there is no thinking_budget equivalent, so a degenerate thinking loop consumes the whole task budget. vLLM (the real harness) enforces `thinking_budget`, so this failure mode is Ollama-specific.
Decision: the Ollama proxy is used thinking-off only (`--llm-kwarg reasoning_effort=none`). Thinking-on evaluation waits for vLLM on the MSI (installing) or the 31B on Kaggle.
