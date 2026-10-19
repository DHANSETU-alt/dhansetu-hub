#!/bin/zsh
set -euo pipefail

check() {
  local name="$1" url="$2"
  local http_status
  http_status="$(curl -sS -m 3 -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true)"
  [[ -n "$http_status" ]] || http_status=000
  if [[ "$http_status" == "200" ]]; then
    echo "$name: OK ($http_status)"
  else
    echo "$name: UNAVAILABLE ($http_status)"
    return 1
  fi
}

check api http://127.0.0.1:8787/api/health
check web http://127.0.0.1:3000/
