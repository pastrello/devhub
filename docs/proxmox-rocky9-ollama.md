# DevHub lab: Proxmox VE 9 + Rocky Linux 9 LXC + RTX 3060 Ti

## Observed environment (2026-11-22)
- GPU: NVIDIA GeForce RTX 3060 Ti, 8192 MiB VRAM.
- Driver shown by nvidia-smi: 620.73.04; advertised CUDA compatibility: 13.5.
- Idle: 9 MiB memory used, 0% utilization, no listed processes.
- nvidia-smi proves device visibility, not that an unprivileged inference process can use CUDA.
- In LXC the kernel NVIDIA driver belongs to the Proxmox host. Do not install kernel driver into container.

## Why separate non-root users?
Root may install system packages, service users and systemd units. A dedicated ollama user runs the inference service and a devhub user runs the orchestrator. Future agent code, repository contents and generated commands are not safe to execute as root. Proxmox unprivileged-LXC and process non-root are different safeguards. Check /dev/nvidia* permissions, cgroups, device maps and user/group IDs in Proxmox if GPU access fails; do not chmod 666 as a workaround.

## Explicit bootstrap (experimental)
Inspect scripts/bootstrap-ollama-lxc.sh and snapshot container first. It does not alter NVIDIA drivers or the Proxmox host. It will refuse to overwrite existing Ollama. Requires curl, tar, zstd, systemd and a mapped NVIDIA device. HTTPS vendor download is used; an independent package signature/hash check is a future hardening requirement.

```bash
bash scripts/bootstrap-ollama-lxc.sh --check
sudo bash scripts/bootstrap-ollama-lxc.sh --install
curl -fsS http://127.0.0.1:11434/api/tags
```

Systemd service is bound only to 127.0.0.1:11434. Do not publish the unauthenticated Ollama API to the network. For future additional containers, use an authenticated TLS reverse proxy/tunnel.

## First GPU and DevHub tests
The local model library has tags qwen3:4b, gemma3:4b and qwen2.5-coder:7b. Start small, after checking license and free disk. Model size, context length and KV cache determine actual VRAM use; 8 GB advertised capacity does not guarantee 7B completely resident.

```bash
ollama pull qwen3:4b
ollama run qwen3:4b 'Responda em uma frase: o que e PostgreSQL?'
ollama ps
nvidia-smi

# As the separate unprivileged development user, after cloning repository:
./install.sh
export PATH="$HOME/.local/bin:$PATH"
devhub doctor
devhub discover
devhub --approve-local qwen3:4b plan 'Explique uma consulta SQL'
devhub --approve-local qwen3:4b run 'Explique uma consulta SQL' --trust-local-endpoint
```

A working nvidia-smi alone is insufficient: verify ollama ps reports GPU usage and inspect nvidia-smi while model is loaded. If Ollama falls back to CPU, inspect journalctl -u ollama -n 100 --no-pager and Proxmox host mapping/permissions. No customer credentials or project secrets in command arguments.

## Product intent: Engine Manager
The bootstrap is temporary. DevHub must offer an integrated engine directory (Ollama, llama.cpp, vLLM, LiteLLM), machine/GPU inventory, license/disk/VRAM-informed model search, approved engine/model installation and upgrades, lifecycle management and benchmarks. Engine installation is privileged setup; model inference and task execution run without root. Later work expands to separately authenticated workers across LXC hosts.

## References
- https://github.com/ollama/ollama/blob/main/docs/linux.mdx
- https://github.com/ollama/ollama/blob/main/docs/gpu.mdx
- https://ollama.com/library/qwen3
- https://forum.proxmox.com/threads/proxmox-older-nvidia-gpus-gtx-1060-p4000-v100-lxc-passthrough-guide-updated-june-2026.183835/
