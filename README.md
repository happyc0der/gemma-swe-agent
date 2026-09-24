# gemma-swe-agent

Solo entry for the Kaggle **Google - The Gemma 4 Developer Agent Competition** (Sep 23 - Dec 2, 2026): post-train and scaffold `gemma-4-31b-it-qat-w4a16-ct` into an autonomous software-engineering agent that fixes real GitHub issues offline on 4x L4 GPUs.

Status: day 1. See `docs/competition.md` for the competition digest and `docs/HARNESS_README.md` for the organizers' harness spec.

## Layout
- `submission/` - exactly what gets zipped and uploaded (YAML agent config, prompts, skills, adapters).
- `harness/` - `swelite`, a faithful local re-implementation of the unreleased `swegemma` evaluator (Docker sandboxes, the 9 tools, ADK compile, verification).
- `experiments/` - one folder per run with config snapshot, results and notes.
- `training/` - trajectory conversion and LoRA training (phase 2).
- `kaggle/` - notebooks for free-tier GPU evaluation and training.
- `paper/` - paper-track write-up.

## Constraints I chose
$0 cloud spend (Kaggle free GPU hours only), a 16 GB laptop GPU as the dev box, no proprietary-model distillation.
