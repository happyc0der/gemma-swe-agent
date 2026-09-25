# swelite vs the official swegemma harness: known differences

The official `swegemma` / `adk-submission` / `adk-eval-core` packages are unreleased (forum thread 2026-09-23), so `harness/` re-implements the behaviour described in `docs/HARNESS_README.md`. The daily Kaggle submission is the ground truth; local numbers are for iteration. Known or suspected deviations:

| Area | Official (per README) | swelite | Risk |
|---|---|---|---|
| Standard instructions 0-5 in the initial prompt | Summarised only, not quoted | Our own wording in `runner.build_agent_prompt` | Low-medium: affects the model's default behaviour; keep our system prompt self-sufficient |
| Test dependency install | Streams a cached site-packages built from the wheel set, then `setup.py --fast-path` | Runs `setup.py` slow path, then `pip install --no-index --find-links=/wheels -e /workspace` (repo's own pins) | Some repos may get different dependency versions; gold/null checks over all 129 tasks measure this |
| `!include ../x` | README says `..` is blocked, but the organizers' sample uses `../prompts/analyzer.md` | Allowed when the resolved path stays inside the submission root | None if the sample compiles officially |
| Skills (`skills:`, `run_skill_script`, `load_skill_resource`) | Supported; scripts run in the task container and debit the budget | Implemented with ADK's `SkillToolset` + a sandbox `BaseEnvironment`; scripts materialize under `/opt/skills` (outside /workspace); each run debits one tool call. Stock ADK requires kebab-case skill names (the README's `repo_navigation` example would fail), so we use kebab-case only | Tool set exposed may differ (ADK also adds `list_skills`, `load_skill`) |
| Thinking config to vLLM | README implies thinking is on by default and `thinking_level: NONE` disables it, so their `adk-submission` layer must translate `thinking_config` | google-adk 2.9.2's `LiteLlm` does **not** translate `thinking_config` for OpenAI-compatible backends, so swelite runs are thinking-off unless `--llm-kwarg reasoning_effort=high` (or `chat_template_kwargs.enable_thinking`) is passed; vLLM then returns a `reasoning_content` channel but enforces no thinking budget (a `<|think|>` system line does nothing) | Medium: local runs may under- or over-think relative to the real harness |
| Sandbox CPU/RAM limits | Docker 4 GiB / 2 vCPU | Same for Docker backend; subprocess backend has no limits | Timing-sensitive tests could differ |
| Container reuse / warm pool | Reused with wiped /workspace | Fresh container per task | Only affects setup time |
| Editing engine | `apply_replacement` 3-tier | Re-implemented from the description | Edge cases in flexible/regex tiers may differ |
| Graph tool symbol resolution | 4 tiers | Same tiers; ties broken by shortest name | Could pick a different node on ambiguous short names |
| `search_similar_code` | resolves query against node keys | Same; observed cosine sims are ~0.99 for everything (embeddings weakly discriminative) | Tool may be less useful than it looks |
| Host architecture | x86_64 (4x L4 box) | On Apple Silicon the sandbox runs under `--platform linux/amd64` emulation (the wheel cache is manylinux x86_64; native arm64 images silently fall back to pydantic v1 and break fastapi). Build needs the buildx plugin (`brew install docker-buildx`) | Emulation is 2-5x slower; timing-sensitive tests differ |
| Test-only dependencies | Organizers' private image ("zero private wheels" in the public Dockerfile) | Local image adds a layer of PyPI test deps (dirty-equals, inline-snapshot, pytest-httpbin, attrs, ...) at build time; `swebench-sandbox:public` is the pure image | Local env may be more permissive than the hidden one |
| ADK version | Unknown; Kaggle's notebook image ships **google-adk 1.29.0** (seen 2026-09-25), and the scoring likely runs on Kaggle infrastructure | swelite uses google-adk 2.9.2 | Medium: instruction templating (`{var?}` optional syntax), compaction and LiteLlm behaviour differ across major versions; the submission prompt avoids optional-template syntax for this reason |
| Snapshot ownership | unknown | `chown -R root:root` + `safe.directory *` (needed: tarballs carry a foreign uid) | None |

Validation status (2026-09-24, amd64 image with local extras): **gold 109/129, null 0/129**. Per repo gold: fastapi 63/67, rich 41/48, requests 4/13, httpx 1/1. The 20 residual gold failures are environment residue, not harness logic:
- requests (9): `TestTimeout::test_connect_timeout` family (connect timeouts behave differently with `network_mode=none`) and one TLS test (`trustme` cert lacks an Authority Key Identifier under the current OpenSSL). Only these fail; the rest of each file passes.
- rich (7): ANSI rendering assertions that depend on the pygments version (2.21 in the wheel cache) and one attrs repr test.
- fastapi (4): starlette-version-dependent router fallbacks and one header-model validation message.
These tasks are excluded from the local dev/holdout scoring denominators via `experiments/splits.json` `env_unstable` (they still run; results just aren't trusted).

Cross-check 2026-09-24: the same sweep natively on the MSI (WSL2, x86_64 Docker, concurrency 8) gives identical results (gold 109/129, null 2/129, same task lists) at ~15 s per gold task and ~29 s per null task, so the Mac's amd64 emulation is faithful and the residuals are real environment differences.

Earlier sweep on the arm64 image without extras: gold 47/129 (pydantic v1 fallback broke fastapi).
