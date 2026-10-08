#!/usr/bin/env bash
set -uo pipefail

if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  ACCENT=$'\e[1m'; GREEN=$'\e[1;32m'; RED=$'\e[1;31m'; MUTED=$'\e[2m'; RESET=$'\e[0m'
else
  ACCENT=''; GREEN=''; RED=''; MUTED=''; RESET=''
fi

printf '%s  ✦ CLEANUP%s  /  Arch Linux и производные\n\n' "$ACCENT" "$RESET"

declare -a cache_dirs=()
for manager in yay paru pikaur trizen pakku pacaur aura pamac; do
  for path in "$HOME/.cache/$manager" "${XDG_CACHE_HOME:-$HOME/.cache}/$manager"; do
    [[ -d "$path" && ! -L "$path" ]] || continue
    duplicate=0
    for existing in "${cache_dirs[@]}"; do
      [[ "$existing" == "$path" ]] && duplicate=1 && break
    done
    (( duplicate )) || cache_dirs+=("$path")
  done
done

printf 'Будут проверены: кэш pacman, yay, paru, pikaur, trizen, pakku, pacaur, aura и pamac.\n'
if (( ${#cache_dirs[@]} )); then
  printf 'Найдены каталоги кэша AUR-менеджеров:\n'
  printf '  %s\n' "${cache_dirs[@]}"
else
  printf 'Каталоги кэша AUR-менеджеров не обнаружены.\n'
fi
printf '\nТакже: пользовательский кэш приложений, корзина и журналы старше 7 дней.\n'
printf '%s\n' 'Кэш некоторых приложений будет создаваться заново. Закрой приложения перед очисткой.'
read -r -p 'Продолжить? [y/N] ' answer
[[ "$answer" =~ ^[yYдД]$ ]] || { echo 'Отменено.'; exit 0; }

before=$(df -B1 --output=used "$HOME" | tail -n 1 | tr -d ' ')
failed=0

if command -v paccache >/dev/null 2>&1; then
  sudo paccache -rk1 || failed=1
  sudo paccache -ruk0 || failed=1
else
  printf '%sНе найден paccache (пакет pacman-contrib).%s\n' "$RED" "$RESET"
  failed=1
fi

cache_root="${XDG_CACHE_HOME:-$HOME/.cache}"
if [[ -d "$cache_root" && ! -L "$cache_root" ]]; then
  find "$cache_root" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + || failed=1
fi
if [[ "$cache_root" != "$HOME/.cache" && -d "$HOME/.cache" && ! -L "$HOME/.cache" ]]; then
  find "$HOME/.cache" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + || failed=1
fi

if command -v gio >/dev/null 2>&1; then
  gio trash --empty || failed=1
elif [[ -d "$HOME/.local/share/Trash/files" ]]; then
  find "$HOME/.local/share/Trash/files" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + || failed=1
  if [[ -d "$HOME/.local/share/Trash/info" ]]; then
    find "$HOME/.local/share/Trash/info" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + || failed=1
  fi
fi

if command -v journalctl >/dev/null 2>&1; then
  sudo journalctl --vacuum-time=7d || failed=1
fi

after=$(df -B1 --output=used "$HOME" | tail -n 1 | tr -d ' ')
freed=$((before-after))
(( freed < 0 )) && freed=0
printf '\n%sОсвобождено приблизительно: %s%s\n' "$GREEN" "$(numfmt --to=iec --suffix=B "$freed")" "$RESET"
df -h "$HOME"
exit "$failed"
