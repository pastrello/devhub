#!/usr/bin/env bash
# DevHub lab: install Ollama without changing Proxmox/NVIDIA kernel drivers.
set -Eeuo pipefail
umask 077
usage() { echo 'Usage: bootstrap-ollama-lxc.sh --check | --install' >&2; exit 2; }
[[ $# == 1 ]] || usage
case "$1" in --check|--install) mode=$1 ;; *) usage ;; esac
[[ -r /etc/os-release ]] || { echo 'Cannot detect OS' >&2; exit 1; }
source /etc/os-release
[[ "${ID:-}" == rocky && "${VERSION_ID%%.*}" == 9 ]] || { echo 'This bootstrap targets Rocky Linux 9 LXC only.' >&2; exit 1; }
echo "System: ${PRETTY_NAME:-Rocky Linux 9}"
echo "Virtualization: $(systemd-detect-virt --container 2>/dev/null || echo unknown)"
if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || true
else
  echo 'WARNING: nvidia-smi not available; verify GPU mapping before install.' >&2
fi
for dev in /dev/nvidiactl /dev/nvidia0 /dev/nvidia-uvm; do
  if [[ -e "$dev" ]]; then ls -l "$dev"; else echo "WARNING: missing $dev" >&2; fi
done
[[ $mode == --check ]] && exit 0
[[ $EUID -eq 0 ]] || { echo 'Installation needs root INSIDE the LXC; use sudo.' >&2; exit 1; }
for cmd in curl tar zstd systemctl useradd; do
  command -v "$cmd" >/dev/null || { echo "Missing $cmd. Install prerequisite manually with dnf." >&2; exit 1; }
done
[[ -d /run/systemd/system ]] || { echo 'systemd not running: cannot safely create/start service.' >&2; exit 1; }
if command -v ollama >/dev/null || [[ -e /etc/systemd/system/ollama.service ]]; then
  echo 'Ollama is already present. Refusing to overwrite; use an explicit upgrade procedure.' >&2
  exit 1
fi
if ! command -v nvidia-smi >/dev/null || [[ ! -e /dev/nvidiactl ]]; then
  echo 'NVIDIA prerequisites not met; fix LXC device passthrough on Proxmox first.' >&2
  exit 1
fi
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
url='https://ollama.com/download/ollama-linux-amd64.tar.zst'
echo "Downloading official Ollama Linux AMD64 package from $url"
curl --fail --location --show-error --silent --proto '=https' --tlsv1.2 --output "$work/ollama.tar.zst" "$url"
tar --zstd -tf "$work/ollama.tar.zst" >/dev/null
mkdir -p "$work/stage"
tar --zstd -xf "$work/ollama.tar.zst" -C "$work/stage" --no-same-owner
# Do not install a superficially valid CLI without its llama.cpp inference engine.
[[ -x "$work/stage/bin/ollama" && -x "$work/stage/lib/ollama/llama-server" ]] || {
  echo 'Incomplete Ollama package: missing bin/ollama or lib/ollama/llama-server; no system files modified.' >&2
  exit 1
}
# Additional independently published checksum/signature verification is still needed.
install -m 0755 "$work/stage/bin/ollama" /usr/bin/ollama
mkdir -p /usr/lib
cp -a "$work/stage/lib/ollama" /usr/lib/ollama
[[ -x /usr/lib/ollama/llama-server ]] || { echo 'Inference engine missing after extraction' >&2; exit 1; }
if ! id -u ollama >/dev/null 2>&1; then
  useradd -r -s /sbin/nologin -U -m -d /usr/share/ollama ollama
fi
install -d -o ollama -g ollama -m 0750 /var/lib/ollama /var/lib/ollama/models
cat > /etc/systemd/system/ollama.service <<'SERVICE'
[Unit]
Description=Ollama local inference (DevHub lab)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/ollama serve
User=ollama
Group=ollama
Environment="HOME=/usr/share/ollama"
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_MODELS=/var/lib/ollama/models"
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE
systemctl daemon-reload
systemctl enable --now ollama
systemctl --no-pager --full status ollama || true
echo 'Verify: curl -fsS http://127.0.0.1:11434/api/tags'
echo 'Verify GPU after pulling and running a small model: ollama ps; nvidia-smi'
echo 'Do not expose TCP 11434 publicly. Device permissions may need adjustment on the Proxmox host.'
