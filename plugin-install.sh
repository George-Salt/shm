#!/usr/bin/env bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/i18n.sh"
SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEST="${SHM_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/shm}/plugins"
if (( $# != 1 )); then
  printf "$(shm_t 'Использование: bash plugin-install.sh <путь-к-плагину>\n')" >&2
  exit 2
fi
PLUGIN="$(cd -- "$1" && pwd -P)"
ID="${PLUGIN##*/}"
[[ "$ID" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ ]] || { echo "$(shm_t 'Некорректный ID плагина')" >&2; exit 1; }
[[ -f "$PLUGIN/plugin.conf" && ! -L "$PLUGIN/plugin.conf" ]] || { echo "$(shm_t 'Отсутствует plugin.conf')" >&2; exit 1; }
ENTRY="$(sed -n 's/^entry=//p' "$PLUGIN/plugin.conf" | head -n1)"
ENTRY="${ENTRY:-main.sh}"
[[ "$ENTRY" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]*\.sh$ && "$ENTRY" != *..* && -f "$PLUGIN/$ENTRY" && ! -L "$PLUGIN/$ENTRY" ]] || { echo "$(shm_t 'Некорректный entry')" >&2; exit 1; }
mkdir -p "$DEST"
TARGET="$DEST/$ID"
if [[ -e "$TARGET" ]]; then
  printf "$(shm_t 'Плагин %s установлен. Заменить? [y/N] ')" "$ID"
  read -r ANSWER
  [[ "$ANSWER" =~ ^[yYдД]$ ]] || exit 0
fi
TMP="$(mktemp -d "$DEST/.${ID}.XXXXXX")"
trap 'rm -rf -- "$TMP"' EXIT
cp -a -- "$PLUGIN"/. "$TMP"/
if [[ -e "$TARGET" ]]; then
  BACKUP="$(mktemp -d "$DEST/.${ID}.backup.XXXXXX")"
  mv -- "$TARGET" "$BACKUP/original"
  if ! mv -- "$TMP" "$TARGET"; then
    mv -- "$BACKUP/original" "$TARGET"
    exit 1
  fi
  rm -rf -- "$BACKUP"
else
  mv -- "$TMP" "$TARGET"
fi
trap - EXIT
printf "$(shm_t 'Установлен плагин: %s\n')" "$ID"
