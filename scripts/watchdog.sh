#!/usr/bin/env bash
set -euo pipefail
max_attempts="${MAX_ATTEMPTS:-999999}"
interval="${WATCH_INTERVAL:-10}"
for ((attempt=1; attempt<=max_attempts; attempt++)); do
  code=$(curl -L -sS -o /dev/null -w '%{http_code}' --max-time 20 https://dhansetuhub.in/api/health || true)
  printf '%s attempt=%s public=%s\n' "$(date -Is)" "$attempt" "$code"
  if [[ "$code" == 200 ]]; then
    printf '# Launch success\n\nPublic health returned HTTP 200 on attempt %s.\n' "$attempt" > LAUNCH_SUCCESS.md
    exit 0
  fi
  sleep "$interval"
done
exit 1
