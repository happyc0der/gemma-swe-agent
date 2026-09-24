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

## 3. Hugging Face (Keshav, once)
Accept the Gemma license at https://huggingface.co/google/gemma-4-31B-it-qat-w4a16-ct and run `huggingface-cli login` on the Mac and inside WSL. Also add `HF_TOKEN` as a Kaggle notebook secret.

## 4. What Claude does next over SSH
1. Clone `happyc0der/gemma-swe-agent` into WSL, `uv venv`, install `harness/`.
2. Copy the dataset from the Mac (`rsync` over Tailscale) or `kaggle competitions download` inside WSL.
3. `swelite build-image`, then the full 129-task gold/null sweep.
4. Serve `gemma-4-12b-it` (vLLM W4A16 in WSL2 with `--tool-call-parser gemma4 --reasoning-parser gemma4`, or Ollama `gemma4:12b` as a fallback) and run the dev split.
