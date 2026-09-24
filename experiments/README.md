# Experiment log

One directory per run: `experiments/<date>-<slug>/` containing
- `config/` : snapshot of `submission/` as run (agent.yaml, prompts, configs, eval_config.yaml)
- `summary.json` : from `swelite eval` (resolution_rate, per-repo, errors, timing)
- `task_results.jsonl`
- `notes.md` : hypothesis, what changed vs the previous run, result, failure taxonomy counts, decision

Rules
1. One change per experiment.
2. Same task set for comparable numbers: `dev` (89) for iteration, `holdout` (40) for confirmation, both fixed in `experiments/splits.json`.
3. Model used is recorded (proxy 12B on Mac/MSI, 31B on Kaggle T4x2, or the real 4x L4 via the daily Kaggle submission).
4. Kaggle submissions are logged in `experiments/kaggle_submissions.md` with the config snapshot dir and the public score.

Failure taxonomy (tag each unresolved task with one primary bucket):
- `no_patch` never produced a diff (narrated, no tool calls, or gave up)
- `wrong_location` edited the wrong file/function
- `edit_mismatch` edit_file could not find old_string / repeated failed edits
- `truncated` tool call cut by max_output_tokens
- `broke_tests` patch applied but tests fail
- `apply_failed` patch could not be applied in the verify container
- `budget` ran out of time/tool calls/turns with work in progress
- `scratch_leak` patch polluted by repro scripts or pytest.ini/conftest.py edits
