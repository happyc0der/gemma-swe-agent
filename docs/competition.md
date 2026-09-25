# Competition digest: Google - The Gemma 4 Developer Agent Competition

Source: https://www.kaggle.com/competitions/gemma-4-developer-agent (read 2026-09-24) and `docs/HARNESS_README.md` (dataset copy).

## Timeline (all 23:59 UTC)
- 2026-09-23 start
- 2026-11-12 paper track deadline (optional, $35k pool, separate sign-up)
- 2026-11-25 entry + team merger deadline
- 2026-12-02 final submission deadline

## Prizes
$37k / $18k / $10k for places 1-3. Winners must open-source code + adapters (Apache-2.0 style) and provide a reproducible write-up.

## Rules that matter
- 1 submission per day, 2 final picks, team max 5 (we are solo).
- External data/models allowed if freely accessible to all ("Reasonableness" standard). Open question on the forum about proprietary-API distillation; no answer yet.
- Public sharing of code must go through the Kaggle forum/notebooks. No private sharing.

## What is scored
- Hidden test set: ~120 tasks from **private repos** (not the 4 public ones), 50/50 public/private LB split.
- Score = fraction of tasks where the agent's patch, applied to a fresh checkout, makes the hidden `test_patch` tests pass (`pytest` exit 0).
- Agent has **12 hours total** to produce patches for all tasks (sandbox setup included, verification excluded).

## Submission format (`submission.zip`, < 3 GiB unpacked)
```
agent.yaml                 # required root (LlmAgent by default)
configs/sampling.yaml      # generate_content_config via !include
prompts/*.md               # instruction via !include; {problem_description} and {hints} are templated from session state
sub_agents/*.yaml          # AgentTool / sub_agents
skills/<name>/SKILL.md     # + scripts/ (run in sandbox) + resources/
adapters/<name>/adapter_config.json + adapter_model.safetensors   # PEFT LoRA, rank <= 128, up to 8
eval_config.yaml           # optional per-task budgets (timeout_seconds, max_tool_calls, max_time_minutes, max_turns)
```
Declarative only; no Python entrypoints; no `..`/symlinks; allowed extensions: yaml/yml/md/txt/py(skills)/json/safetensors.

## Model and serving
- Only `gemma-4-31b-it-qat-w4a16-ct` (INT4 QAT, compressed-tensors, ~17 GB weights). One base model per submission; per-agent LoRA adapters allowed.
- Served by vLLM on 4x L4 (96 GB): `tensor_parallel_size=4`, `gpu_memory_utilization=0.9`, `max_model_len=32768`, `enable_lora`, `max_loras=8`, `max_lora_rank=128`, `tool_call_parser=gemma4`, `reasoning_parser=gemma4`.
- ADK talks to it via LiteLlm `openai/<model>` at `http://127.0.0.1:8000/v1`, 5 retries.
- `generate_content_config` allowed fields: temperature, top_p, top_k, max_output_tokens (<= 32768, default 16384), penalties, stop_sequences, seed, thinking_config {thinking_level MINIMAL..HIGH|NONE, thinking_budget <= 32768 (default 4096), include_thoughts}.

## Tools (fixed set, JSON string results)
| tool | budgeted | notes |
|---|---|---|
| run_command(command) | yes | bash -c in /workspace, timeout min(300s, remaining), stdout/stderr truncated to 5000 chars |
| read_file(filepath, start_line, end_line) | yes | 1-indexed inclusive; cap 150 lines AND 10000 chars; `is_truncated` |
| edit_file(filepath, old_string, new_string, allow_multiple=False) | yes | exact -> whitespace-flexible -> regex-tokenized match; error if 0 or >1 matches |
| write_file(filepath, content) | yes | mkdir -p; overwrite |
| get_status() | no | budget + patch status |
| submit_patch() | no | `git add -N . && git diff HEAD`; ends session after the turn |
| get_code_neighbors(node, edge_type, max_neighbors=50) | yes | 4-tier symbol resolution |
| search_similar_code(query, k=10) | yes | query must be a SYMBOL NAME (resolved against node keys), not NL |
| get_code_subgraph(nodes) | yes | induced subgraph |
Graph tools are only offered when graph/embedding files > 100 bytes exist for the repo.

## Session protocol
- Initial user message: task header + problem statement (+ hints) + budget block + environment rules + 6 standard instructions + code-intel tools note + `find . -maxdepth 3` listing (150 entries).
- Loop until submit_patch, time/turn/tool budget exhaustion, or 3 consecutive no-tool-call turns. Nudges: "continue / call submit_patch", with special messages for truncated `<|tool_call>` and MAX_TOKENS.
- If no submit_patch, the harness still extracts `git diff HEAD` and grades it.
- ADK events compaction: interval 15, overlap 2, token_threshold 32768, retention 5. Context cache min 2048 tokens.

## Sandbox
- `python:3.13-slim` + git/patch/pytest, offline (`network_mode=none`), 4 GiB RAM, 2 vCPU, `/workspace`, wheels at `/wheels`, `sandbox/setup.py` installs deps + editable package.
- Harness commits `pytest.ini` and `conftest.py` into the baseline commit: do not modify them.
- Untracked files in /workspace end up in the patch: scratch goes to /tmp.
- Verification: fresh container, 4-pass patch apply, test files named in `test_patch` are reset to HEAD (so editing tests is useless), `test_patch` applied, `PYTHONSAFEPATH=1 python3 -m pytest <targets> -p no:anyio -o timeout=0 -q`.

## Public training data (129 tasks)
fastapi 67, rich 48, requests 13, httpx 1. Median reference patch: 31 lines, 1 file. No hints. `snapshots/` = 20.5 GB of repo tarballs. Graph/embedding files exist under two names (task id and `<repo>_<commit>`); Kaggle stored only one copy of each hard-link pair, so exactly 129 of 256 files in each dir are 0 bytes, but 128/129 tasks have usable data under one of the names.

## Sample submission (the organizers' starter)
Root `LlmAgent` with all 9 tools + a `code_analyzer` AgentTool (read-only, graph tools), two dummy rank-4 LoRAs (q_proj/o_proj, layer 0 only), sampling temp 0.2 / thinking high with 4096 budget / 16384 max tokens, and an `eval_config.yaml` of 1 minute, 10 tool calls, 50 turns per task (which is why the day-1 leaderboard is mostly zeros; top is 0.08).

## Structural constraint: no in-task compaction (verified in google-adk 2.9.2)
`EventsCompactionConfig` runs only **after a completed invocation** (`Runner._run_post_invocation_compaction`), and its token trigger requires the latest prompt to already be >= `token_threshold` (32768), which vLLM rejects before it can happen (`max_model_len` 32768). Within one agent turn (the whole task until a nudge) the context only grows. With `read_file`/`run_command` outputs capped at 5000 chars (~1.3k tokens) plus the ~3.5k-token initial prompt, a trajectory overflows after roughly 20 full-size tool outputs and the task dies with `ContextWindowExceededError` (the fallback diff is still graded). Consequences: keep tool outputs small, plan for <= 20-25 tool calls, submit early; `max_tool_calls` above ~30 is mostly moot.

## Known unknowns
- `swegemma`, `adk-submission`, `adk-eval-core` are not published (forum question open). We re-implement (`harness/`).
- Organizers' concurrency inside the 12 h cap.
- Whether proprietary-API distillation is allowed. Our stance: no Claude/Gemini-generated data regardless.
- vLLM issue #50059: rank-32 all-layer LoRA on compressed-tensors W4A16 was unstable; rank-8 partial-layer fine. Gate before training.
