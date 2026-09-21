#!/usr/bin/env bash
set -euo pipefail
STORAGE_ROOT="${DHANSETU_STORAGE_ROOT:-/mnt/dhansetu-data}"
EXPECTED_UUID="${DHANSETU_STORAGE_UUID:-}"
if [[ ! -d "$STORAGE_ROOT" ]] || ! mountpoint -q "$STORAGE_ROOT"; then
  echo "DhanSetu storage guard: $STORAGE_ROOT is not a mounted filesystem" >&2
  exit 78
fi
if [[ -n "$EXPECTED_UUID" ]]; then
  actual="$(findmnt -no UUID --target "$STORAGE_ROOT")"
  [[ "$actual" == "$EXPECTED_UUID" ]] || { echo "DhanSetu storage guard: UUID mismatch" >&2; exit 78; }
fi
for dir in app-data postgres documents backups logs; do install -d -m 0750 "$STORAGE_ROOT/$dir"; done
echo "DhanSetu storage guard: OK ($STORAGE_ROOT)"
