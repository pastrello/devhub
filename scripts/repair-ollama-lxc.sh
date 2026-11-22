#!/usr/bin/env bash
# Validate/repair the Ollama runtime installed by DevHub's Rocky 9 LXC bootstrap.
set -Eeuo pipefail
umask 077
if [[ $# != 1 || ( $1 != --check && $1 != --repair ) ]]; then
  echo 'Usage: repair-ollama-lxc.sh --check | --repair' >&2; exit 2
fi
mode=$1
source /etc/os-release
[[ "${ID:-}" == rocky && "${VERSION_ID%%.*}" == 9 ]] || { echo 'Rocky Linux 9 only' >&2; exit 1; }
echo "Ollama binary: $(command -v ollama || echo missing)"
echo "Ollama server: $(systemctl is-active ollama 2>/dev/null || true)"
echo "Client version: $(/usr/bin/ollama --version 2>&1 || true)"
for f in /usr/bin/ollama /usr/lib/ollama/llama-server; do
  if [[ -x "$f" ]]; then ls -lh "$f"; else echo "MISSING OR NOT EXECUTABLE: $f"; fi
done
[[ $mode == --check ]] && exit 0
[[ $EUID -eq 0 ]] || { echo 'Run --repair with root inside the LXC' >&2; exit 1; }
[[ -f /etc/systemd/system/ollama.service ]] || { echo 'Expected DevHub lab systemd unit not found' >&2; exit 1; }
[[ -x /usr/bin/ollama ]] || { echo 'Expected /usr/bin/ollama not found' >&2; exit 1; }
for cmd in curl tar zstd systemctl sha256sum; do
  command -v "$cmd" >/dev/null || { echo "Missing prerequisite: $cmd" >&2; exit 1; }
done
if [[ -x /usr/lib/ollama/llama-server ]]; then
  echo 'Runtime already present; aborting no-op. If inference fails, inspect journalctl -u ollama.' >&2; exit 0
fi
work=$(mktemp -d /var/tmp/devhub-ollama-repair.XXXXXXXX)
backup=/var/backups/devhub-ollama-$(date -u +%Y%m%dT%H%M%SZ)
changed=0
completed=0
restore() {
  code=$?
  if [[ $completed == 0 && $changed == 1 ]]; then
    echo 'Repair failed; restoring previous Ollama files' >&2
    rm -rf /usr/lib/ollama
    rm -f /usr/bin/ollama
    [[ -e "$backup/lib" ]] && mv "$backup/lib" /usr/lib/ollama || true
    [[ -e "$backup/bin" ]] && mv "$backup/bin" /usr/bin/ollama || true
    systemctl start ollama || true
  fi
  rm -rf "$work"
  exit "$code"
}
trap restore EXIT
mkdir -p "$work/stage"
url='https://ollama.com/download/ollama-linux-amd64.tar.zst'
echo "Downloading official archive $url (not changing service yet)"
curl --fail --location --show-error --silent --proto '=https' --tlsv1.2 --output "$work/ollama.tar.zst" "$url"
sha256sum "$work/ollama.tar.zst"
tar --zstd -tf "$work/ollama.tar.zst" > "$work/manifest.txt"
tar --zstd -xf "$work/ollama.tar.zst" -C "$work/stage" --no-same-owner
if [[ ! -x "$work/stage/bin/ollama" || ! -x "$work/stage/lib/ollama/llama-server" ]]; then
  echo 'OFFICIAL ARCHIVE DOES NOT INCLUDE bin/ollama AND lib/ollama/llama-server.' >&2
  echo 'Nothing modified; package may be incomplete or unsuitable for this Ollama version.' >&2
  grep 'lib/ollama/.*server' "$work/manifest.txt" | head -20 >&2 || true
  exit 1
fi
# Reject a symlink resolving outside of the extraction root.
for f in "$work/stage/bin/ollama" "$work/stage/lib/ollama/llama-server"; do
  resolved=$(readlink -f "$f")
  [[ $resolved == "$work/stage/"* ]] || { echo 'Archive path escapes staging directory' >&2; exit 1; }
done
mkdir -p "$backup"
echo 'Stopping Ollama, preserving existing binary/libraries in backup'
systemctl stop ollama
changed=1
[[ -e /usr/bin/ollama ]] && mv /usr/bin/ollama "$backup/bin"
[[ -e /usr/lib/ollama ]] && mv /usr/lib/ollama "$backup/lib"
install -m 0755 "$work/stage/bin/ollama" /usr/bin/ollama
cp -a "$work/stage/lib/ollama" /usr/lib/ollama
[[ -x /usr/lib/ollama/llama-server ]] || { echo 'Post-install runtime verification failed'; exit 1; }
systemctl start ollama
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:11434/api/version
echo
completed=1
echo "Repair installed. Backup kept in: $backup"
echo 'Next: ollama run qwen3:4b "Teste"; ollama ps; nvidia-smi'
echo 'Note: successful version API check is not proof of working inference or GPU usage.'
