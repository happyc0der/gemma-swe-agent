# Kaggle GPU hours ledger (account `dankaxon`)

Kaggle's free tier gives about 30 GPU hours per week (T4x2 counts as one session). The CLI cannot read the
remaining quota; the authoritative number is on the Kaggle profile page ("GPU quota"). Hours below are
push-to-finish wall time from this project's logs, so they slightly overstate use when a kernel waited in a queue.
The account also runs other projects' kernels (biohub-*, electric-car), which draw on the same quota.

## Policy
- Evaluation compute is Kaggle (decision 2026-09-26); the MSI laptop is a demo workbench only.
- A GPU run must be able to change a decision: validate a config the proxy cannot separate, calibrate the
  proxy against a Kaggle LB score, or gate LoRA. No exploratory sweeps on GPU hours.
- A full 33-task holdout run of the real 31B on T4x2 costs about 3.5-4 h (sequential, time-bound tasks).
  At ~30 h/week that is at most ~6 runs, so keep at most one queued at a time and keep ~6 h in reserve.
- Log every push here with its purpose; fill in the hours when it finishes.

## Week of 2026-09-25

| kernel / version | accelerator | start (UTC) | end (UTC) | hours | purpose / outcome |
|---|---|---|---|---|---|
| gemma4-31b-vllm-probe v1-v5 | T4x2 | 09-25 14:04 | ~15:50 | ~1.7 | vLLM W4A16 on Turing: all 5 failed |
| gemma4-31b-llamacpp-probe v1-v2 | T4x2 | 09-25 14:44 | ~15:30 | ~0.7 | llama.cpp Q4_0 works |
| gemma4-31b-holdout-eval v1 | T4x2 | 09-25 15:32 | ~15:58 | ~0.4 | setup failure |
| gemma4-31b-holdout-eval v2 | T4x2 | 09-25 15:58 | 16:38 | 0.7 | setup iteration |
| gemma4-31b-holdout-eval v3 | T4x2 | 09-25 16:40 | 17:31 | 0.9 | setup iteration |
| gemma4-31b-holdout-eval v4 | T4x2 | 09-25 17:33 | 18:33 | 1.0 | setup iteration |
| gemma4-31b-holdout-eval v5 | T4x2 | 09-25 18:37 | 20:28 | 1.9 | first partial holdout (1/33, OOM kills) |
| gemma4-31b-holdout-eval v6 | T4x2 | 09-25 20:30 | 21:01 | 0.5 | error (mmap flag) |
| gemma4-31b-holdout-eval v7 | T4x2 | 09-25 21:03 | 09-26 01:18 | 4.3 | error after long run (server SIGKILL) |
| gemma4-31b-holdout-eval v8 | T4x2 | 09-26 01:22 | 05:10 | 3.8 | day-3 config: 3/33 |
| gemma4-31b-holdout-eval v9 | T4x2 | 09-26 05:24 | 09:26 | 4.0 | v4.2: 2/33 |
| gemma4-official-l4-eval v1 | T4x2 (L4 unavailable) | 09-26 16:23 | 16:26 | 0.05 | L4x4 not granted; exited at GPU check |
| gemma4-31b-holdout-eval v10 | T4x2 | 09-26 19:01 (queued from 16:29) | 22:33 | 3.5 | day-4 config (v4.3, 4.5 min): 1/33, 12.1 calls/task, 32/33 time-bound |
| **total so far** | | | | **~23.4** | ~6.6 h left if the quota is 30 h; hold it for calibration after the day-4 score |

Setup iterations (v1-v7) cost ~9.7 h; that one-off cost is now paid, and each further holdout run is ~4 h.

## Week of 2026-10-03 (quota week assumed reset; check the Kaggle profile for the exact figure)

| kernel / version | accelerator | start (UTC) | end (UTC) | hours | purpose / outcome |
|---|---|---|---|---|---|
| gemma4-env-check v1-v4 | **CPU only** | 10-03 06:17 | 07:26 | 0 GPU | validate the faithful sandbox (kaggle/faithful_sandbox.py): v4 = gold 33/33, null 0/33, ~11 s per verification |
| gemma4-faithful-eval v1 | T4x2 | 10-03 07:31 | 10:19 | 2.8 | prompt v4.5: **7/16**; found temp-0.2 verbatim loops, repro rewriting, late/no edits |
| gemma4-faithful-eval v2 | T4x2 | 10-03 10:40 | 12:50 | 2.4 | prompt v4.6: **8/16** (v4.5 7/16), loops 3 -> 0, median first edit 33 -> 18 |
| gemma4-faithful-eval v3 | T4x2 | 10-03 13:20 | 15:31 | 2.5 | prompt v4.7: **8/16** (ties v4.6), no-edit 3 -> 1, hangs 2 -> 0; memory fix: 1 kill (was 3-5) |
| gemma4-faithful-eval v4 | T4x2 | 10-03 ~15:45 | 18:16 | 2.6 | prompt v4.8: **8/16** (same set as v4.7) but exact duplicate calls 77 -> 130; the empty-grep rule described the wrong output form; kept v4.7 for day 10 |
| gemma4-faithful-eval v5 | T4x2 | 10-03 18:31 | 21:40 | 3.1 | prompt v4.9: **7/16**; the note made the model emit empty thought-channel markers (7 prose-only replies), 4 timeouts; dropped |
| gemma4-faithful-eval v6 | T4x2 | 10-03 21:45 | 10-04 00:12 | 2.45 | prompt v5.0n: **9/16** (best; all earlier solves kept + fastapi_12942), fewest repeats and timeouts; day 11 |
| **total this week** | | | | **~15.9** | GPU runs paused until the day 10-12 scores are in |

Quota fact (observed 2026-10-10): the 30 h weekly GPU quota resets Saturday 00:00 UTC.

## 2026-10-08 onward (Keshav: do thinking-on and LoRA, cheaper first)

| kernel / version | accelerator | start (UTC) | end (UTC) | hours | purpose / outcome |
|---|---|---|---|---|---|
| gemma4-faithful-eval v7 | T4x2 | 10-08 03:53 | 07:12 | 3.3 | v5.0n thinking on: **6/16** vs 9/16 off (9 session timeouts; fewer loops); not submitted |
| gemma4-lora-gate v1-v4 | T4x2 | 10-08 07:16 | 08:05 | 0.8 | QLoRA of the 31B fits only up to 3,072 tokens (60 s/step); trajectories are 7k-17k: not viable on T4x2 |
| gemma4-faithful-eval v8 | T4x2 | 10-08 14:11 | 16:45 | 2.5 | prompt v5.1: **8/16** (sibling rule solves rich_3480; malformed-edit loop cost requests_6644) |
| gemma4-faithful-eval v9 | T4x2 | 10-08 16:47 | 19:07 | 2.3 | prompt v5.2: **8/16**, 0 malformed-call errors (v5.1: 35); within noise of v5.0n 9 |
| gemma4-faithful-eval v10 | T4x2 | 10-09 14:29 | 21:14 | 6.6 | set B v5.0n vs v5.2: **invalid** (unpinned llama.cpp HEAD made every call ramble; all tasks timed out) |
| gemma4-faithful-eval v11 | T4x2 | 10-10 00:17 | 00:52 | 0.6 | failed at import: the 10-09 wheelhouse (swegemma 0.2.11) removed swegemma.models.registry |
| gemma4-faithful-eval v12 | T4x2 | 10-10 01:09 | 05:35 | 4.4 | set B under the new harness: v5.0n **4/17**, v5.2 2/17 (33-task totals 13 vs 10); v5.0n stays |
| gemma4-faithful-eval v13 | T4x2 | 10-11 14:38 | 17:30 | 2.9 | v5.0n on set A under the new harness: **9/16** (same 9 tasks as the old harness); 33-task baseline 9 + 4 = 13/33 |
| (not pushed) | | 10-11 | | 0 | v5.3 (convention rule for warnings/exceptions) staged as CFG `{"variants": [v53], "subset": "AB"}`; push deferred because v13 is still running (one kernel at a time) |
| gemma4-faithful-eval v14 | T4x2 | 10-12 13:06 | ~17:00 | 3.9 | v5.3 on subset AB: **13/29**, then OOM-killed (agent repro on rich_3480 ate the 32 GB host RAM; no memory cap in the subprocess sandbox, now fixed with ulimit -v 4 GB). Ties v5.0n on the same 29 tasks; not shipped |
| gemma4-faithful-eval v15 | T4x2 | 10-14 13:07 | 17:22 | 4.24 | v5.4 (edit first, then one check script) on subset AB: **13/33**, ties v5.0n; 11 no-edit tasks vs 4; not shipped |
| gemma4-faithful-eval v16 | T4x2 | 10-15 13:04 | 17:34 | 4.49 | v5.5 (v5.0n + read_file tool) on subset AB: **9/33** vs v5.0n 13/33; malformed read_file/edit_file loops; not shipped |
| gemma4-faithful-eval v17 | T4x2 | 10-16 13:06 | 17:37 | 4.52 | v5.6 (v5.0n without edit_file; all edits via a run_command fix script) on subset AB: **11/33** vs v5.0n 13/33; 0 malformed calls, but submit_patch sent to the shell in 17 tasks; not shipped |
| gemma4-faithful-eval v18 | T4x2 | 10-17 13:14 | 17:29 | 4.25 | v5.7 (v5.6 + submit_patch is a tool, not a shell command) on subset AB: **12/33** vs v5.0n 13/33; submit_patch-in-shell down to 8 calls; not shipped |
| gemma4-faithful-eval v19 | T4x2 | 10-18 13:15 (queued; ran 17:04) | 21:28 | 4.39 | v5.8 (v5.7 + budget-warning protocol) on subset AB: **14/33** vs v5.0n 13/33, first result above the baseline; fastapi_5624 solved for the first time; **shipped** as v58-t45 |
| gemma4-faithful-eval v20 | T4x2 | 10-19 13:09 (queued; ran 18:11) | 22:21 | 4.16 | v5.9 (v5.8 + fix-script template as an `edit()` helper call so half-written scripts fail instead of silently doing nothing) on subset AB: **12/33** vs v5.8 14/33; silent no-op scripts 29 -> 4 but 35 assert failures took their place (edit success rate unchanged at 47%); not shipped |
| gemma4-faithful-eval v21 | T4x2 | 10-20 13:17 | 17:44 | 4.46 | v6.0 (v5.9 with a five-line `edit()` helper: indentation-tolerant line match, re-indents new, prints the file's real lines on a miss) on subset AB, for the ship rule vs v5.8 14/33 |
| gemma4-faithful-eval v22 | T4x2 | 10-21 13:10 | (superseded) | ~0.1 | pushed before the pub-budget-fit-off variant was on GitHub (the kernel clones the repo); replaced by v23 minutes later |
| gemma4-faithful-eval v23 | T4x2 | 10-21 13:13 | | (est. 4.5) | pub-budget-fit-off (the official-starter budget-fit prompt, thinking OFF, 8 min x3 / 28 calls) on subset AB: offline baseline for the bf-warn screen (v24 next) and the first offline number for the public prompt vs v5.8 14/33 |
| **total since 10-03** | | | | **~64.3** | |

Quota week from Sat 10-10 00:00 UTC: v11 0.6 + v12 4.4 + v13 2.9 = 7.9 h used; with v14 (est. 4.5) ~12.4 h of 30.

Quota week from Sat 10-10 00:00 UTC (updated 10-14): v11 0.6 + v12 4.4 + v13 2.9 + v14 3.9 = 11.8 h used; with v15 (est. 4.5) ~16.3 h of 30. Resets Sat 10-17 00:00 UTC.

Quota week from Sat 10-10 00:00 UTC (updated 10-15): v11 0.6 + v12 4.4 + v13 2.9 + v14 3.9 + v15 4.24 = 16.0 h used; with v16 (est. 4.5) ~20.5 h of 30. Resets Sat 10-17 00:00 UTC.

Quota week from Sat 10-10 00:00 UTC (updated 10-16): v11 0.6 + v12 4.4 + v13 2.9 + v14 3.9 + v15 4.24 + v16 4.49 = 20.5 h used; with v17 (est. 4.5) ~25.0 h of 30 (~5 h left). Resets Sat 10-17 00:00 UTC.

Quota week from Sat 10-10 00:00 UTC (final): 20.5 + v17 4.52 = 25.0 h of 30.

Quota week from Sat 10-17 00:00 UTC: 0 h used before v18; with v18 (est. 4.5) ~4.5 h of 30. Resets Sat 10-24 00:00 UTC.

Quota week from Sat 10-17 00:00 UTC (updated 10-18): v18 4.25 h used; with v19 (est. 4.5) ~8.8 h of 30. Resets Sat 10-24 00:00 UTC.

Quota week from Sat 10-17 00:00 UTC (updated 10-19): v18 4.25 + v19 4.39 = 8.6 h used; with v20 (est. 4.5) ~13.1 h of 30. Resets Sat 10-24 00:00 UTC.

Quota week from Sat 10-17 00:00 UTC (updated 10-20): v18 4.25 + v19 4.39 + v20 4.16 = 12.8 h used; with v21 (est. 4.5) ~17.3 h of 30. Resets Sat 10-24 00:00 UTC.

Quota week from Sat 10-17 00:00 UTC (updated 10-21): v18 4.25 + v19 4.39 + v20 4.16 + v21 4.46 = 17.3 h used; with v23 (est. 4.5) ~21.8 h of 30. Resets Sat 10-24 00:00 UTC.
