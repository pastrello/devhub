#!/usr/bin/env bash
set -euo pipefail
umask 077
cd -- "$(dirname -- "$0")"
if [[ $EUID == 0 ]]; then echo 'Run as an unprivileged user.' >&2; exit 1; fi
python_bin=${PYTHON_BIN:-python3.12}
command -v "$python_bin" >/dev/null || { echo 'Install Python 3.12 first (Rocky 9/10: sudo dnf install python3.12, if available).' >&2; exit 1; }
"$python_bin" -c 'import sys; assert sys.version_info >= (3,12)'
install -d -m 700 "$HOME/.local/lib/devhub" "$HOME/.local/bin"
install -m 600 devhub.py "$HOME/.local/lib/devhub/devhub.py"
install -m 600 engine_manager.py "$HOME/.local/lib/devhub/engine_manager.py"
printf '#!/usr/bin/env bash\nexec %q %q "$@"\n' "$(command -v "$python_bin")" "$HOME/.local/lib/devhub/devhub.py" > "$HOME/.local/bin/devhub"
chmod 700 "$HOME/.local/bin/devhub"
"$HOME/.local/bin/devhub" --version
echo 'Add ~/.local/bin to PATH if needed. No services, provider logins or paid resources were created.'
