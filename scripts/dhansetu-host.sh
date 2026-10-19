#!/bin/zsh
# DhanSetu production host guard. The SSD path must be supplied explicitly;
# this script never guesses a volume and never writes into an absent mount.
set -euo pipefail

ROOT="/Users/apple/shakthi-os"
SSD_ROOT="${DHANSETU_SSD_ROOT:-}"

require_ssd() {
  if [[ -z "$SSD_ROOT" ]]; then
    echo "ERROR: DHANSETU_SSD_ROOT is not configured; refusing to start." >&2
    echo "Set it only after confirming the real external SSD mount, e.g." >&2
    echo "  export DHANSETU_SSD_ROOT=/Volumes/<confirmed-volume>/DhanSetu" >&2
    return 2
  fi
  if [[ ! -d "$SSD_ROOT" ]]; then
    echo "ERROR: required SSD path does not exist: $SSD_ROOT" >&2
    return 2
  fi
  local mount_point
  mount_point="$(df -P "$SSD_ROOT" | awk 'NR==2 {print $NF}')"
  if [[ "$mount_point" == "/" || "$mount_point" == "/System/Volumes/Data" ]]; then
    echo "ERROR: $SSD_ROOT resolves to internal storage ($mount_point); refusing to start." >&2
    return 2
  fi
  mkdir -p "$SSD_ROOT"/{data,db,documents,backups,logs}
  touch "$SSD_ROOT/.dhansetu-storage-check"
  rm "$SSD_ROOT/.dhansetu-storage-check"
}

case "${1:-check-storage}" in
  check-storage)
    require_ssd
    echo "DhanSetu SSD storage verified: $SSD_ROOT"
    ;;
  start)
    require_ssd
    exec "$ROOT/dashboard/node_modules/.bin/next" start --hostname 127.0.0.1 --port 3000
    ;;
  *)
    echo "Usage: $0 check-storage|start" >&2
    exit 2
    ;;
esac
