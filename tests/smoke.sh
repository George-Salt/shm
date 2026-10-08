#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
for script in shm shm-cli install.sh plugin-install.sh plugins/*/main.sh tests/smoke.sh; do
  bash -n "$script"
done
python3 - <<'PY'
import ast
from pathlib import Path
ast.parse(Path('tui.py').read_text())
PY
sandbox="$(mktemp -d)"
trap 'rm -rf -- "$sandbox"' EXIT
export HOME="$sandbox/home" SHM_HOME="$sandbox/data/shm" NO_COLOR=1
mkdir -p "$HOME" "$sandbox/hello"
bash install.sh </dev/null
[[ ! -e "$SHM_HOME/plugins/cleanup" ]]
"$HOME/.local/bin/shm" help >/dev/null
"$HOME/.local/bin/shm" list >/dev/null
printf 'name=Hello\ndescription=Smoke fixture\nentry=main.sh\n' > "$sandbox/hello/plugin.conf"
printf '#!/usr/bin/env bash\nprintf "argument=%%s\\n" "$1"\nexit "${2:-0}"\n' > "$sandbox/hello/main.sh"
bash plugin-install.sh "$sandbox/hello"
output="$("$HOME/.local/bin/shm" list)"
grep -q Hello <<< "$output"
output="$("$HOME/.local/bin/shm" info hello)"
grep -q 'Smoke fixture' <<< "$output"
output="$("$HOME/.local/bin/shm" run hello 'two words')"
grep -q 'argument=two words' <<< "$output"
status=0
"$HOME/.local/bin/shm" run hello test 7 >/dev/null || status=$?
[[ "$status" == 7 ]]
printf 'n\n' | "$HOME/.local/bin/shm" remove hello >/dev/null
[[ -d "$SHM_HOME/plugins/hello" ]]
printf 'y\n' | "$HOME/.local/bin/shm" remove hello >/dev/null
[[ ! -e "$SHM_HOME/plugins/hello" ]]
printf 'entry=../escape.sh\n' > "$sandbox/hello/plugin.conf"
if bash plugin-install.sh "$sandbox/hello" >/dev/null 2>&1; then
  echo 'Invalid entry unexpectedly accepted' >&2
  exit 1
fi
printf 'Smoke checks passed.\n'
