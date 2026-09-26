# Paper-track outline (due 2026-11-12) — working title

**"Harness fidelity is the first hyperparameter: what a scaffold-only Gemma 4 agent needs on a $0 budget"**

## Claims we can already support with evidence in `experiments/`
1. Tool-schema fidelity dominates prompt quality. Under the scorer's stack (google-adk 1.36.1 + vLLM 0.19.1)
   optional integer parameters are serialized as `any_of`/`INTEGER`/`NULL`, the model quotes the numbers, and
   `read_file` line ranges fail 100% of the time. A proxy on a newer ADK hid this completely (7/33 vs 0.00).
   Evidence: `docs/harness-fidelity.md`, `/tmp/adk_probe.py` results in `experiments/2026-09-27-day4/notes.md`,
   official-harness runs `off-v41-holdout-partial` vs `off-v43-holdout`.
2. Context is the binding constraint, not turns or time: ADK compaction never fires inside a task; trajectories die
   after ~20 full-size tool outputs; a "context budget" prompt moved overflow from 12/33 tasks to 2/33.
3. Sampling temperature controls loop failures in small agents (0.2 loops, 0.7 does not) and interacts with thinking.
4. Sub-agent isolation (read-only analyzer via AgentTool) as a compaction substitute: measure `off-v43-analyzer-holdout`.
5. The real 31B on free hardware: llama.cpp on Kaggle T4x2 reproduces the scorer's model within noise
   (3/33 on the day-3 config) once page-cache accounting is handled (`LLAMA_ARG_MMAP=0`).

## Method section
- `swelite` re-implementation (before the wheelhouse), then the official harness on the same GPU box; dev/holdout
  split (`experiments/splits.json`, 22 env-unstable tasks excluded, seed 20260924).
- Noise band: repeated runs of one config differ by up to 3/33; only differences > 3 are reported as effects.
- Every daily Kaggle submission is logged with a config snapshot (`experiments/kaggle_submissions.md`).

## Ablation table to fill (33-task holdout, official harness, 12B proxy; confirm top rows with the 31B on Kaggle)
| config | resolved | read_file errors | overflow | submit calls | notes |
|---|---|---|---|---|---|
| sample prompt, no adapters, thinking off | | | | | organizers' baseline |
| v4.1 (line-range reads) | | | | | |
| v4.2 (string-only args, sed ranges) | | | | | |
| v4.3 (read_file removed) | | | | | day-4 submission |
| v4.3 + read-only analyzer | | | | | |

## Open items
- LoRA gate (vLLM W4A16 + named LoRA modules; organizer confirms adapters are served as `--lora-modules`).
- Budget policy under the 12 h sequential cap once the organizers score unfinished tasks as 0.
