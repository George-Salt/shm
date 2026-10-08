#!/usr/bin/env bash
set -euo pipefail
# Capture explicit language before the shared resolver exports its default.
INSTALL_LANGUAGE="${SHM_LANG:-}"
case "$#:${1:-}" in
  0:) ;;
  1:--help|1:-h)
    printf 'Usage / Использование: bash install.sh [--lang en|ru]\n'
    exit 0
    ;;
  2:--lang)
    [[ "$2" == en || "$2" == ru ]] || { echo 'Language / Язык: en | ru' >&2; exit 2; }
    INSTALL_LANGUAGE="$2"
    export SHM_LANG="$2"
    ;;
  *) echo 'Usage / Использование: bash install.sh [--lang en|ru]' >&2; exit 2 ;;
esac
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/i18n.sh"
SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEST="${SHM_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/shm}"
BIN="$HOME/.local/bin"
if [[ -t 0 && -z "$INSTALL_LANGUAGE" ]]; then
  printf 'Select language / Выберите язык:\n  1) English\n  2) Русский\n'
  while true; do
    if ! read -r -p 'Language / Язык [1/2, en/ru]: ' INSTALL_LANGUAGE; then
      printf '\nInstallation cancelled / Установка отменена.\n' >&2
      exit 1
    fi
    case "$INSTALL_LANGUAGE" in
      1|en|EN) SHM_LANG=en; break ;;
      2|ru|RU) SHM_LANG=ru; break ;;
      *) printf 'Choose 1 (en) or 2 (ru) / Выберите 1 (en) или 2 (ru).\n' ;;
    esac
  done
  export SHM_LANG
fi
command -v python3 >/dev/null || { echo "$(shm_t 'Нужен Python 3')"; exit 1; }
mkdir -p "$DEST/plugins" "$BIN"
install -m 755 "$SOURCE/shm" "$BIN/shm"
install -m 755 "$SOURCE/shm-cli" "$DEST/shm-cli"
install -m 644 "$SOURCE/tui.py" "$DEST/tui.py"
for file in i18n.py translations.json i18n.sh VERSION; do
  install -m 644 "$SOURCE/$file" "$DEST/$file"
done
install -m 755 "$SOURCE/plugin-install.sh" "$DEST/plugin-install.sh"
# Persist the installer selection so the first application launch matches it.
printf '%s\n' "$SHM_LANG" > "$DEST/language.tmp"
mv -- "$DEST/language.tmp" "$DEST/language"
OLD="$DEST/plugins/alice"
if [[ -f "$OLD/plugin.conf" ]] && grep -qx 'name=Alice' "$OLD/plugin.conf" && grep -q '^MAC=' "$OLD/main.sh" 2>/dev/null; then
  rm -rf -- "$OLD"
fi
if [[ -t 0 ]]; then
  read -r -p "$(shm_t 'Установить плагины, включённые в архив? [y/N] ')" INSTALL_PLUGINS
else
  INSTALL_PLUGINS='n'
fi
if [[ "$INSTALL_PLUGINS" =~ ^[yYдД]$ ]]; then
  for dir in "$SOURCE"/plugins/*; do
    [[ -d "$dir" ]] || continue
    bash "$SOURCE/plugin-install.sh" "$dir"
  done
fi
printf "$(shm_t 'SHM установлен: %s/shm\nПлагины: %s/plugins\n')" "$BIN" "$DEST"
printf "$(shm_t 'Для fish: fish_add_path ~/.local/bin\n')"
