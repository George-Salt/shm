#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
for script in shm shm-cli install.sh plugin-install.sh plugins/*/main.sh i18n.sh tools/build_release.sh tests/smoke.sh; do
  bash -n "$script"
done
python3 - <<'PY'
import ast
from pathlib import Path
for path in ('tui.py', 'i18n.py', 'tools/build_catalog.py', 'tests/test_i18n.py'):
    ast.parse(Path(path).read_text())
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
# Both languages, persisted preferences, and environment overrides.
for ident in cleanup bluetooth-speaker; do
  bash plugin-install.sh "plugins/$ident"
done
unset SHM_LANG
"$HOME/.local/bin/shm" lang en >/dev/null
output="$("$HOME/.local/bin/shm" info cleanup)"
grep -q 'System cleanup' <<< "$output"
"$HOME/.local/bin/shm" lang ru >/dev/null
output="$("$HOME/.local/bin/shm" info cleanup)"
grep -q 'Очистка системы' <<< "$output"
output="$(SHM_LANG=en "$HOME/.local/bin/shm" info cleanup)"
grep -q 'System cleanup' <<< "$output"
for language in en ru; do
  output="$(printf 'n\n' | SHM_LANG="$language" bash "$SHM_HOME/plugins/cleanup/main.sh")"
  if [[ "$language" == en ]]; then grep -q 'Cancelled.' <<< "$output"; else grep -q 'Отменено.' <<< "$output"; fi
  # Stub hardware commands: verify localized Bluetooth errors without device operations.
  mkdir -p "$sandbox/bin"
  printf '#!/usr/bin/env bash\nexit 1\n' > "$sandbox/bin/bluetoothctl"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$sandbox/bin/wpctl"
  chmod +x "$sandbox/bin/bluetoothctl" "$sandbox/bin/wpctl"
  output="$(PATH="$sandbox/bin:$PATH" SHM_LANG="$language" bash "$SHM_HOME/plugins/bluetooth-speaker/main.sh" 2>&1)" && exit 1
  if [[ "$language" == en ]]; then grep -q 'Unable to enable Bluetooth.' <<< "$output"; else grep -q 'Не удалось включить Bluetooth.' <<< "$output"; fi
done
"$HOME/.local/bin/shm" --version | grep -Fq "SHM $(cat VERSION)"
python3 tests/test_i18n.py
python3 tests/test_terminal.py
python3 tests/test_installer.py
printf 'Smoke checks passed.\n'
