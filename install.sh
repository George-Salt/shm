#!/usr/bin/env bash
set -euo pipefail
SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEST="${SHM_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/shm}"
BIN="$HOME/.local/bin"
command -v python3 >/dev/null || { echo 'Нужен Python 3'; exit 1; }
mkdir -p "$DEST/plugins" "$BIN"
install -m 755 "$SOURCE/shm" "$BIN/shm"
install -m 755 "$SOURCE/shm-cli" "$DEST/shm-cli"
install -m 644 "$SOURCE/tui.py" "$DEST/tui.py"
install -m 755 "$SOURCE/plugin-install.sh" "$DEST/plugin-install.sh"
OLD="$DEST/plugins/alice"
if [[ -f "$OLD/plugin.conf" ]] && grep -qx 'name=Alice' "$OLD/plugin.conf" && grep -q '^MAC=' "$OLD/main.sh" 2>/dev/null; then
  rm -rf -- "$OLD"
fi
if [[ -t 0 ]]; then
  read -r -p 'Установить плагины, включённые в архив? [y/N] ' INSTALL_PLUGINS
else
  INSTALL_PLUGINS='n'
fi
if [[ "$INSTALL_PLUGINS" =~ ^[yYдД]$ ]]; then
  for dir in "$SOURCE"/plugins/*; do
    [[ -d "$dir" ]] || continue
    bash "$SOURCE/plugin-install.sh" "$dir"
  done
fi
printf 'SHM установлен: %s/shm\nПлагины: %s/plugins\n' "$BIN" "$DEST"
printf 'Для fish: fish_add_path ~/.local/bin\n'
