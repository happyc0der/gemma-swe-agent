# Proxy batch: prompt v3, Gemma 4 12B (Ollama, 32k ctx, thinking off), same 4 tasks, 12 min / 40 calls

Result: 0/4 resolved, but 2/4 produced applied patches that fail exactly one hidden test (requests_7205: 205 passed / 1 failed; fastapi_11355: 1 failed). Both were extracted by the harness fallback (agent ran out of time before submit_patch).
rich_2725 and rich_3454: 20+ identical edit_file calls with escaped quotes/newlines in the anchor; the loop-escape rule was ignored. rich_3454 eventually tried sed and a /tmp/fix.py script (the fallback rule worked) but ran out of budget.

Taxonomy: broke_tests 2 (near-miss fixes), edit_mismatch 2 (escaped anchors + repetition loop).
Change vs v2: patches now appear (0 -> 2 of 4). Loop rule needs the model to notice repetition; without thinking the 12B does not.
Decision: v3 ships as day 2. Next lever is model-side (thinking on the 31B) rather than more prompt text; evaluate v3 on the 31B on Kaggle T4x2 once HF access exists.
