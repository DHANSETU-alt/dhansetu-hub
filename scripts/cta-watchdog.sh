#!/usr/bin/env bash
set -euo pipefail
while :; do
  origin=$(curl -sS -o /dev/null -w '%{http_code}' https://dhansetu-hub.onrender.com/api/health || true)
  public=$(curl -sS -o /dev/null -w '%{http_code}' https://dhansetuhub.in/api/health || true)
  printf '%s origin=%s public=%s\n' "$(date -Is)" "$origin" "$public" | tee LIVE_STATUS.md
  if [[ "$origin" == 200 && "$public" == 200 ]]; then exit 0; fi
  sleep 30
done
