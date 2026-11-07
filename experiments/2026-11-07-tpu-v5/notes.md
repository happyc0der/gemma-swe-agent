# TPU v5 (pushed 11-05 14:07 UTC, ran ~02:00-02:34 UTC 11-07, 0.51 TPU h)

Plan: canary, then pub-budget-fit and bf-t10 (thinking on) on AB and DEV.

What worked (same as v4): weights in /dev/shm in 52 s, vLLM serving after 585 s, decode 64 tok/s
(time_scale 0.51), memory fine (294/377 GB free, no dirty backlog). The v4 `import rich` fix held:
stage 2 installed the harness and started the canary.

What failed: the canary (fastapi_14303) ended with 0 LLM calls:
`litellm.APIConnectionError ... cannot import name 'CacheableResult' from 'mcp.types'`.
Cause: eval_stage.py installed litellm unpinned, which pulled litellm 1.108.2 (released after our
compile venv was built). That release imports `mcp.types.CacheableResult` (mcp >= 2.2), but google-adk
1.36.1 from the wheelhouse requires mcp >= 1.24,< 2 (mcp 1.30.0 installed).

Reproduced on the Mac: a fresh venv with litellm 1.108.2 + mcp 1.30.0 raises the same ImportError on a
tool-calling `litellm.completion`; the compile venv (litellm 1.104.2 + mcp 1.30.0) gives a plain
connection error on the same call (no import problem).

Fix (v6): pin `litellm==1.104.2` in kaggle/eval_tpu/eval_stage.py, and the same pin in
kaggle/eval_faithful/run.py so the next T4 push cannot hit it. The submission bundle itself is not
affected (the scorer image uses the wheelhouse, not pip). Verified only at the litellm call level on
the Mac; the canary on v6 is the real test.
