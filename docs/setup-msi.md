# MSI laptop setup (Windows, RTX 3080 Ti 16 GB, Tailscale `msi` = 100.90.106.39)

Goal: an always-on Linux-ish dev box reachable from the Mac over Tailscale that can (a) run Docker sandboxes for `swelite`, (b) serve a Gemma 4 12B proxy model on the GPU, (c) hold the 21 GB competition dataset.

## 1. SSH (Keshav, once)
Option A (simplest): Windows OpenSSH Server.
- Settings > System > Optional features > Add > "OpenSSH Server". Then in an admin PowerShell:
  ```powershell
  Set-Service sshd -StartupType Automatic; Start-Service sshd
  New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
  ```
- Put the Mac's public key (`cat ~/.ssh/id_ed25519.pub` on the Mac) into `C:\ProgramData\ssh\administrators_authorized_keys` (admin account) or `C:\Users\<you>\.ssh\authorized_keys` (non-admin), and tell Claude the Windows username.
- Optional: make WSL the default shell for SSH sessions: `New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell -Value "C:\Windows\System32\wsl.exe" -PropertyType String -Force`.

Option B: sshd inside WSL2 on a different port (e.g. 2222) plus a `netsh interface portproxy` rule. More moving parts; use A.

Verify from the Mac: `ssh <user>@msi 'nvidia-smi'`.

## 2. WSL2 + Docker + CUDA (Keshav, once; or Claude over SSH with your approval per install)
- `wsl --install -d Ubuntu-24.04` (admin PowerShell), reboot, create the Linux user.
- Keep the NVIDIA Windows driver current (Game Ready or Studio, 560+). Do NOT install a Linux display driver inside WSL.
- Inside WSL: `nvidia-smi` should already work. Install Docker Engine in WSL (or Docker Desktop with WSL2 backend) and the NVIDIA Container Toolkit if GPU containers are needed (not needed for swelite sandboxes, which are CPU-only).
- Give WSL enough resources in `%UserProfile%\.wslconfig`:
  ```
  [wsl2]
  memory=24GB
  processors=12
  swap=16GB
  ```
- Prevent sleep: Settings > Power > Screen and sleep > Never when plugged in.

## 3. Hugging Face
Not needed: the `google/gemma-4-*-it-qat-w4a16-ct` checkpoints (and the unsloth mirrors) are ungated (`gated: false` via the HF API, verified 2026-09-24). `serve/hf_download.sh` fetches them with plain HTTPS.

## 4. What Claude does next over SSH
1. Clone `happyc0der/gemma-swe-agent` into WSL, `uv venv`, install `harness/`.
2. Copy the dataset from the Mac (`rsync` over Tailscale) or `kaggle competitions download` inside WSL.
3. `swelite build-image`, then the full 129-task gold/null sweep.
4. Serve `gemma-4-12b-it` (vLLM W4A16 in WSL2 with `--tool-call-parser gemma4 --reasoning-parser gemma4`, or Ollama `gemma4:12b` as a fallback) and run the dev split.

## State as of 2026-09-24 (done by Claude over SSH)
- SSH: `ssh msi` works (OpenSSH, PowerShell shell; user `KESHAV`). Long jobs must go through Task Scheduler (`schtasks`), because processes started from an SSH session are killed at logoff.
- WSL2 Ubuntu 22.04 with GPU passthrough; Docker Desktop with WSL integration; in WSL use `DOCKER_CONFIG=~/.docker-ssh` (set in `.bashrc`) to bypass the Windows credential helper.
- Repo at `~/Projects/gemma-swe-agent` in WSL, harness venv at `harness/.venv`, `swebench-sandbox:latest` built natively (x86_64, no emulation).
- Dataset zip at `C:\Users\keshav\gemma-4-developer-agent.zip`, unpacked into `data/competition` in WSL.
- Proxy model: Ollama on Windows, `gemma4:12b-32k` (num_ctx 32768), second server bound to `0.0.0.0:11435` via task `swe_ollama_serve` (script `C:\Users\keshav\ollama_serve.ps1`). Reachable from WSL at the host gateway IP (`ip route | awk '/default/ {print $3}'`) and from the Mac at `100.90.106.39:11435`.
- vLLM venv at `serve/.venv` (install slow: the laptop's PyPI throughput is ~250 KB/s).
- Scheduled tasks: `swe_unzip`, `swe_vllm_install`, `swe_ollama_pull`, `swe_ollama_serve`, `swe_sweeps`.

## vLLM on the MSI (working config as of 2026-09-24 evening)
`serve/vllm_serve.sh`, task `swe_vllm_serve`. Gemma 4 12B W4A16 at ~34 tok/s (compiled mode), KV cache 5.1 GiB (50k tokens, 1.5x concurrency at 32k). Things that bit, in order:
1. torch.compile and FlashInfer's sampler both JIT with `nvcc`, which WSL lacks and cannot apt-install without sudo: `uv pip install nvidia-cuda-nvcc` into the venv, set `CUDA_HOME`/`PATH` to `.venv/lib/python3.12/site-packages/nvidia/cu13`, and `VLLM_USE_FLASHINFER_SAMPLER=0` (the sampler JIT still failed).
2. Memory: Windows holds ~1.1-1.6 GiB of the 16 GiB, so `--gpu-memory-utilization 0.88`; drop `--enable-lora` (its buffers pushed KV cache negative), `--max-num-seqs 2`, `--max-num-batched-tokens 4096`, `--limit-mm-per-prompt '{"image":0,"audio":0}'`.
3. Port 8000 lives inside WSL's NAT: reachable at 127.0.0.1 from WSL (where the harness runs) but not from the Mac over Tailscale (Ollama on Windows is reachable because it binds on the host).
4. `schtasks /run` is a no-op while a previous instance is still "Running": `schtasks /end` first, then `/run`.
5. **Trap:** Task Scheduler stops running tasks when the laptop switches to battery (default `StopIfGoingOnBatteries`) and won't start them on battery; on 2026-09-25 08:08 EDT every job (vLLM, a batch, its sandboxes) died at the same instant with no error. After creating a task, run in PowerShell: `Set-ScheduledTask -TaskName <name> -Settings (New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable)`. Applied to all `swe_*` tasks.
6. **Trap:** `/sc once /st 23:59` also fires at 23:59 local even if you `/run` it immediately. On 2026-09-24 every one-shot job re-ran at once at 23:59 EDT (sweeps, batches, queued runs), each `rm -rf`-ing its results dir and flooding vLLM. Create one-shot tasks with a start date in the past so the trigger never fires: `/sc once /st 00:00 /sd 01/01/2020`, then `/run`. Copy results to the Mac as soon as a run finishes.
7. **Trap:** tasks that run `wsl.exe` or `powershell` in the interactive session flash a console window at every launch (Keshav saw the screen flashing). Launch them through `C:\Users\keshav\hidden.vbs` (a WScript `Run cmd, 0` wrapper): `/tr "wscript.exe //B C:\Users\keshav\hidden.vbs wsl.exe -d Ubuntu -- bash /home/keshav/<script>.sh"`. All `swe_*` tasks were re-registered this way on 2026-09-25.

## Official harness on the MSI (added 2026-09-26)

- `~/wheelhouse/` holds the pure-Python wheels from the Kaggle wheelhouse dataset; `~/offvenv` is a
  uv venv (`uv venv --python 3.12`, then `uv pip install --find-links ~/wheelhouse google-adk==1.36.1
  google-genai==2.11.0 adk-submission==0.2.11 adk-eval-core==0.1.0 swegemma==0.2.7`). WSL's system
  python has no `venv` module, so use uv.
- `~/off_eval.sh` (env: `RUN`, `SUB`, `MINUTES`, `CALLS`, `TURNS`, `TIMEOUT`) runs
  `swegemma eval --sandbox docker` on the 33 usable holdout tasks against the local vLLM 12B proxy via
  a generated `models.yaml` that aliases `gemma-4-31b-it-qat-w4a16-ct` to the served 12B. Results in
  `harness/results/<RUN>/` (task_results.jsonl, summary.json, logs/, traces/, patches/) plus
  `<RUN>.console`.
- `~/off_queue.sh` lists runs back to back; scheduled task `swe_off_eval` launches it hidden. Trap 8:
  `schtasks /end` does not kill the WSL process tree, so `pkill -f "swegemma eval"` (and kill the
  `off_queue.sh` bash) before re-running the task, or two queues run at once.
