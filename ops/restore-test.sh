#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STORAGE_ROOT="${DHANSETU_STORAGE_ROOT:-/mnt/dhansetu-data}"
"$ROOT/scripts/storage-guard.sh"
latest="$(find "$STORAGE_ROOT/backups" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2- || true)"
[[ -n "$latest" ]] || { echo "No backup available" >&2; exit 1; }
(cd "$latest" && sha256sum -c SHA256SUMS)
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
tar -xzf "$latest"/repository-*.tar.gz -C "$tmp"
test -f "$tmp/package.json"
echo "Restore test passed for $latest"
