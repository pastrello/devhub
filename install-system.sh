#!/usr/bin/env bash
# System-wide DevHub installer: privileged setup; non-root runtime.
set -Eeuo pipefail
umask 077
[[ $# == 1 ]] || { echo 'Usage: install-system.sh --check | --install | --rollback' >&2; exit 2; }
mode=$1
case "$mode" in --check|--install|--rollback) ;; *) exit 2 ;; esac
cd -- "$(dirname -- "$0")"
[[ -f devhub.py && -f engine_manager.py ]] || { echo 'Missing DevHub sources' >&2; exit 1; }
command -v python3.12 >/dev/null || { echo 'Python 3.12 required. Install from Rocky Linux package repositories.' >&2; exit 1; }
python3.12 -c 'import sys; assert sys.version_info >= (3,12)'
if [[ $mode == --check ]]; then
  echo 'DevHub engine manager: sources and Python 3.12 OK'
  command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true
  command -v ollama >/dev/null && ollama --version || true
  echo 'No changes made. --install requires root and provisions /opt/devhub, /usr/local/bin/devhub and an isolated user.'
  exit 0
fi
[[ $EUID == 0 ]] || { echo 'Administrative install/rollback requires root inside the LXC.' >&2; exit 1; }
command -v runuser >/dev/null && command -v useradd >/dev/null || { echo 'runuser and useradd are required' >&2; exit 1; }
base=/opt/devhub
current="$base/current"
previous="$base/previous"
if [[ $mode == --rollback ]]; then
  [[ -L $previous ]] || { echo 'No previous release available for rollback.' >&2; exit 1; }
  target=$(readlink -f "$previous")
  [[ -d $target && -f $target/devhub.py ]] || { echo 'Previous release invalid.' >&2; exit 1; }
  temp="$base/.rollback-$$"
  ln -s "$target" "$temp"
  mv -Tf "$temp" "$current"
  echo "Rolled back to $target"
  exit 0
fi
if ! id -u devhub >/dev/null 2>&1; then
  useradd -r -m -d /var/lib/devhub -s /sbin/nologin devhub
fi
install -d -m 0755 "$base" "$base/releases"
install -d -o devhub -g devhub -m 0700 /var/lib/devhub
release="$base/releases/0.1.1-$(date -u +%Y%m%dT%H%M%SZ)-$$"
install -d -m 0755 "$release"
install -m 0644 devhub.py engine_manager.py "$release/"
# Keep the previous live release addressable for rollback.
if [[ -L $current ]]; then
  target=$(readlink -f "$current")
  [[ -d $target ]] && ln -sfn "$target" "$previous"
fi
ln -s "$release" "$base/.current-$$"
mv -Tf "$base/.current-$$" "$current"
cat > "$base/.devhub-launcher-$$" <<'WRAPPER'
#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -eq 0 ]]; then
  exec runuser -u devhub -- /usr/bin/python3.12 /opt/devhub/current/devhub.py --state /var/lib/devhub "$@"
fi
if [[ $(id -un) == devhub ]]; then
  exec /usr/bin/python3.12 /opt/devhub/current/devhub.py --state /var/lib/devhub "$@"
fi
echo 'DevHub system install runs as devhub: use sudo devhub ... or runuser -u devhub -- devhub ...' >&2
exit 1
WRAPPER
install -m 0755 "$base/.devhub-launcher-$$" /usr/local/bin/devhub
rm -f "$base/.devhub-launcher-$$"
/usr/local/bin/devhub --version
echo 'Installed. Execution occurs as non-root devhub user, including when invoked by root.'
echo 'No cloud services, Ollama models, GPUs, accounts, or package upgrades changed.'
