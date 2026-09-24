# swelite vs the official swegemma harness: known differences

The official `swegemma` / `adk-submission` / `adk-eval-core` packages are unreleased (forum thread 2026-09-23), so `harness/` re-implements the behaviour described in `docs/HARNESS_README.md`. The daily Kaggle submission is the ground truth; local numbers are for iteration. Known or suspected deviations:

| Area | Official (per README) | swelite | Risk |
|---|---|---|---|
| Standard instructions 0-5 in the initial prompt | Summarised only, not quoted | Our own wording in `runner.build_agent_prompt` | Low-medium: affects the model's default behaviour; keep our system prompt self-sufficient |
| Test dependency install | Streams a cached site-packages built from the wheel set, then `setup.py --fast-path` | Runs `setup.py` slow path, then `pip install --no-index --find-links=/wheels -e /workspace` (repo's own pins) | Some repos may get different dependency versions; gold/null checks over all 129 tasks measure this |
| `!include ../x` | README says `..` is blocked, but the organizers' sample uses `../prompts/analyzer.md` | Allowed when the resolved path stays inside the submission root | None if the sample compiles officially |
| Skills (`skills:`, `run_skill_script`, `load_skill_resource`) | Supported; scripts run in the task container and debit the budget | Implemented with ADK's `SkillToolset` + a sandbox `BaseEnvironment`; scripts materialize under `/opt/skills` (outside /workspace); each run debits one tool call. Stock ADK requires kebab-case skill names (the README's `repo_navigation` example would fail), so we use kebab-case only | Tool set exposed may differ (ADK also adds `list_skills`, `load_skill`) |
| Thinking config to vLLM | ADK -> LiteLlm -> vLLM `gemma4` reasoning parser | Same libraries; behaviour with Ollama proxy may differ | Verify on Kaggle with the real model |
| Sandbox CPU/RAM limits | Docker 4 GiB / 2 vCPU | Same for Docker backend; subprocess backend has no limits | Timing-sensitive tests could differ |
| Container reuse / warm pool | Reused with wiped /workspace | Fresh container per task | Only affects setup time |
| Editing engine | `apply_replacement` 3-tier | Re-implemented from the description | Edge cases in flexible/regex tiers may differ |
| Graph tool symbol resolution | 4 tiers | Same tiers; ties broken by shortest name | Could pick a different node on ambiguous short names |
| `search_similar_code` | resolves query against node keys | Same; observed cosine sims are ~0.99 for everything (embeddings weakly discriminative) | Tool may be less useful than it looks |
| Snapshot ownership | unknown | `chown -R root:root` + `safe.directory *` (needed: tarballs carry a foreign uid) | None |

Validation status: gold and null checks pass on `requests_7205` and `rich_2725` with the Docker backend, and on `requests_7205` with the subprocess backend. Full 129-task gold/null sweep pending the dataset download.
