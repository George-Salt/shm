#!/usr/bin/env bash
set -uo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/../../i18n.sh"

fail() { printf '  ✗ %s\n' "$1" >&2; exit 1; }
command -v bluetoothctl >/dev/null || fail "$(shm_t 'Не найден bluetoothctl (bluez).')"
command -v wpctl >/dev/null || fail "$(shm_t 'Не найден wpctl (PipeWire).')"

bluetoothctl power on >/dev/null 2>&1 || fail "$(shm_t 'Не удалось включить Bluetooth.')"

printf "$(shm_t '  ✦ Bluetooth / аудиоустройства\n')"
printf '  ──────────────────────────────────────\n'
printf "$(shm_t '  Поиск устройств (8 секунд)...\n')"
bluetoothctl --timeout 8 scan on >/dev/null 2>&1 || true

mapfile -t devices < <(bluetoothctl devices | sed -nE 's/^Device ([[:xdigit:]]{2}(:[[:xdigit:]]{2}){5}) (.*)$/\1|\3/p' | sort -f -t '|' -k2)
((${#devices[@]})) || fail "$(shm_t 'Устройства не найдены. Переведи колонку в режим сопряжения.')"

printf '\n'
for i in "${!devices[@]}"; do
  name="${devices[i]#*|}"
  mac="${devices[i]%%|*}"
  info="$(bluetoothctl info "$mac" 2>/dev/null || true)"
  state=''
  grep -q 'Connected: yes' <<< "$info" && state="$(shm_t ' · подключено')"
  printf '  %2d  %s%s\n' "$((i+1))" "$name" "$state"
done
printf "$(shm_t '\n  Номер устройства (q — отмена): ')"
read -r choice || exit 0
[[ "$choice" != q && "$choice" != Q ]] || exit 0
[[ "$choice" =~ ^[0-9]+$ ]] && ((choice >= 1 && choice <= ${#devices[@]})) || fail "$(shm_t 'Неверный номер.')"
selected="${devices[choice-1]}"
mac="${selected%%|*}"
name="${selected#*|}"

printf "$(shm_t '\n  Выбрано: %s\n')" "$name"
info="$(bluetoothctl info "$mac" 2>/dev/null || true)"
if ! grep -q 'Paired: yes' <<< "$info"; then
  printf "$(shm_t '  Сопряжение... Подтверди запрос, если появится.\n')"
  bluetoothctl --timeout 25 pair "$mac" || fail "$(shm_t 'Не удалось выполнить сопряжение.')"
fi
bluetoothctl trust "$mac" >/dev/null 2>&1 || true

connected=false
for attempt in 1 2 3; do
  printf "$(shm_t '  Подключение · попытка %d/3\n')" "$attempt"
  if bluetoothctl --timeout 18 connect "$mac" >/dev/null 2>&1 || bluetoothctl info "$mac" 2>/dev/null | grep -q 'Connected: yes'; then
    connected=true
    break
  fi
  sleep 2
done
[[ "$connected" == true ]] || fail "$(shm_t 'Подключить устройство не удалось.')"

mac_key="${mac//:/_}"
card=''
sink=''
for attempt in {1..12}; do
  status="$(wpctl status -n 2>/dev/null || wpctl status 2>/dev/null || true)"
  card="$(awk -v mac="$mac_key" '
    /Cards:/ {area="cards"; next}
    /Sinks:|Sources:|Filters:|Streams:|Video/ {if (area=="cards") area=""}
    area=="cards" && index(tolower($0),tolower(mac)) {if (match($0,/[0-9]+/)) {print substr($0,RSTART,RLENGTH); exit}}
  ' <<< "$status")"
  sink="$(awk -v mac="$mac_key" '
    /Sinks:/ {area="sinks"; next}
    /Sources:|Filters:|Streams:|Video/ {if (area=="sinks") area=""}
    area=="sinks" && index(tolower($0),tolower(mac)) {if (match($0,/[0-9]+/)) {print substr($0,RSTART,RLENGTH); exit}}
  ' <<< "$status")"
  [[ -n "$card" || -n "$sink" ]] && break
  sleep 1
done

if command -v pactl >/dev/null 2>&1; then
  card_name="$(pactl list cards short 2>/dev/null | awk -v mac="$mac_key" 'index(tolower($2),tolower(mac)) {print $2; exit}')"
  if [[ -n "$card_name" ]]; then
    if pactl set-card-profile "$card_name" a2dp-sink >/dev/null 2>&1; then
      printf "$(shm_t '  ✓ Профиль A2DP активирован.\n')"
    else
      printf "$(shm_t '  ! Автовыбор A2DP не удался; продолжаю с текущим профилем.\n')"
    fi
  fi
else
  printf "$(shm_t '  ! Для автоматического выбора A2DP установи pactl (libpulse).\n')"
fi

for attempt in {1..10}; do
  status="$(wpctl status -n 2>/dev/null || wpctl status 2>/dev/null || true)"
  sink="$(awk -v mac="$mac_key" '
    /Sinks:/ {area="sinks"; next}
    /Sources:|Filters:|Streams:|Video/ {if (area=="sinks") area=""}
    area=="sinks" && index(tolower($0),tolower(mac)) {if (match($0,/[0-9]+/)) {print substr($0,RSTART,RLENGTH); exit}}
  ' <<< "$status")"
  [[ -n "$sink" ]] && break
  sleep 1
done
[[ -n "$sink" ]] || fail "$(shm_t 'Соединение есть, но PipeWire не создал аудиовыход. Проверь профиль Bluetooth.')"
wpctl set-default "$sink" || fail "$(shm_t 'Не удалось назначить аудиовыход.')"
wpctl set-volume "$sink" 0.30 || fail "$(shm_t 'Не удалось выставить громкость.')"
printf "$(shm_t '  ✓ Аудиовыход: %s\n  ✓ Громкость: 30%%\n')" "$name"
