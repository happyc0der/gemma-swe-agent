# Faithful eval: prompt v5.2 vs v5.0n and v5.1 (same 16 holdout tasks, "set A")

Kernel v9, 16:47-19:07 UTC, 104 min of agent runs, 2.3 GPU h. v5.2 = v5.0n + sibling rule (grep -n on the exact changed
expression) + "code with triple quotes or backticks goes through /tmp/fix.py, not edit_file" (template uses ''' when
the code contains \"\"\").

| metric | v5.0n | v5.1 | v5.2 |
|---|---|---|---|
| solved | 9 | 8 | 8 |
| malformed-call errors | 0 | 35 | **0** (fix.py used 8 times) |
| exact repeat calls | 51 | 135 | 54 |
| session timeouts | 1 | 1 | 1 |
| agent time | 112 min | 118 min | 104 min |

- Lost vs v5.0n: fastapi_14360 (used all 40 calls, submitted a wrong two-file patch; not affected by the server kill).
- rich_3480 unsolved again (sibling fixed in v5.1, not here); its hidden test then looped and caused the 18:35
  llama-server OOM kill during verification, as in earlier runs.
- 9 / 8 / 8 is within run-to-run noise on 16 tasks: each fix removes the failure it targets, but set A cannot rank
  these versions. Next: v5.0n and v5.2 on set B (the 17 stable holdout tasks set A never uses, `"subset": "B"`),
  ~5 GPU h, after the weekly quota resets. Daily submissions stay on v5.0n until then.
