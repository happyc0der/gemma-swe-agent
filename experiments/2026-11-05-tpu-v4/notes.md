# TPU v4 (ran 11-03) and v5 (pushed 11-05)

v4 (commit a27c0bf; weights in /dev/shm; pushed 11-01 16:50 UTC, queued ~39 h, ran 07:45-08:05 UTC 11-03, 0.32 h) is the
first run in which the whole serving stack worked. The results sat uncollected until 11-05 because no daily routine run
is recorded for 11-03 or 11-04.

| step | result |
|---|---|
| download 62.6 GB to /dev/shm | 51 s (the v1-v3 disk stall is gone) |
| vLLM (vllm-tpu 0.32.0, TP 8, gemma4 tool + reasoning parsers) | up after 600 s |
| check thinking off / on, tool call | all correct (structured reasoning, `read_file` tool call, finish = tool_calls) |
| decode | 64 tok/s, also with an 11.7k-token prompt (TTFT 1.03 s, 0.06 s cached) -> time_scale 0.51 (8 min -> 4.1 min) |
| memory | anon+shmem 77 GB of the 330 GB cgroup limit, no pressure |
| stage 2 | **crashed before the canary: `ModuleNotFoundError: No module named 'rich'`** (rc 1, ALL_DONE at 0.32 h) |

**Cause.** eval_stage.py installs swegemma/adk_eval_core with `--no-deps` and lists their dependencies by hand; the list
came from the T4 kernel, whose image already has rich, numpy and pandas. The TPU harness venv is fresh.

**Fix and check.** Added rich, numpy, pandas. Reproduced locally in a fresh Python 3.12 venv installed in the kernel's
order from data/wheelhouse-2026-10-12: without rich the import section fails with the same error; with the fix it prints
IMPORTS_OK (swegemma 0.2.11) and build_submission_limits works. The rest of stage 2 (canary, Evaluator against vLLM) has
never run on this machine, so it is still unverified. A failed canary now also saves canary.tgz.

**A limit of this lane: thinking_token_budget is not enforced here.** check_budget64 asked for 64 thinking tokens and got
542 reasoning tokens. The request was accepted (vLLM raises an error if reasoning_config is off, and it did not), so the
TPU backend appears to ignore the budget. Consequences: bf-think2k and bf-think8k cannot be screened on this lane (a
budget change has no effect here), and thinking may run somewhat longer than on the scorer in every run, so compare
variants on this lane only with each other, not with LB counts. Sampling changes such as bf-t10 are unaffected, except
that litellm.drop_params may drop top_k (temperature is always sent).

**v5** (CFG["runs"] replaces variants + subset): canary, then base AB, bf-t10 AB, base DEV, bf-t10 DEV, thinking on, one
tgz per run; a run starts only before 5.5 h, so the worst case fits the session. bf-t10 is the only live candidate this lane
can measure. Collect with `--file-pattern '^[^/]*\.(log|txt|json|tgz)$'` into data/tpu_results/v5.
