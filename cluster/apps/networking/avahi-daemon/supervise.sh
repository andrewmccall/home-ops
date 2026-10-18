#!/bin/sh
set -eu
pid=
stop() {
  if [ -n "$pid" ]; then
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
    pid=
  fi
}
fresh() {
  stamp=$(stat -c %Y /run/relay/status.json 2>/dev/null) || return 1
  [ "$(( $(date +%s) - stamp ))" -lt 25 ]
}
trap 'stop; exit 0' TERM INT
while :; do
  if [ ! -s /run/relay/avahi-daemon.conf ] || ! fresh; then
    sleep 1 & wait $! || true
    continue
  fi
  checksum=$(cksum /run/relay/avahi-daemon.conf 2>/dev/null) || continue
  avahi-daemon --no-chroot --no-drop-root --file=/run/relay/avahi-daemon.conf &
  pid=$!
  while fresh && kill -0 "$pid" 2>/dev/null && [ -s /run/relay/avahi-daemon.conf ] && [ "$(cksum /run/relay/avahi-daemon.conf 2>/dev/null || true)" = "$checksum" ]; do
    sleep 1 & wait $! || true
  done
  stop
  sleep 1 & wait $! || true
done
