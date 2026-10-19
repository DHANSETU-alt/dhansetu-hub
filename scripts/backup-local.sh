#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STORAGE_ROOT="${DHANSETU_STORAGE_ROOT:-/mnt/dhansetu-data}"
"$ROOT/scripts/storage-guard.sh"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="$STORAGE_ROOT/backups/$STAMP"
mkdir -p "$DEST"
git -C "$ROOT" archive --format=tar.gz --output="$DEST/repository-$(git -C "$ROOT" rev-parse --short HEAD).tar.gz" HEAD
git -C "$ROOT" rev-parse HEAD > "$DEST/HEAD"
git -C "$ROOT" status --short > "$DEST/git-status.txt"
# Keep durable state, but exclude the backup tree so backups never contain
# themselves. Service secrets remain outside the archive in the root-readable
# environment file and are never read by this script.
tar -czf "$DEST/storage-data.tar.gz" -C "$STORAGE_ROOT" \
  --exclude=backups app-data postgres documents logs
find "$STORAGE_ROOT" -maxdepth 2 -type f ! -path "$STORAGE_ROOT/backups/*" \
  -printf '%M %u:%g %s %p\n' | sort > "$DEST/storage-inventory.txt"
sha256sum "$DEST"/*.tar.gz > "$DEST/SHA256SUMS"
if command -v supabase >/dev/null 2>&1 && [[ -n "${SUPABASE_DB_URL:-}" ]]; then
  supabase db dump --db-url "$SUPABASE_DB_URL" -f "$DEST/supabase.sql"
else
  echo "database dump skipped: configure SUPABASE_DB_URL locally" > "$DEST/database-backup-blocked.txt"
fi
echo "Backup created at $DEST"
