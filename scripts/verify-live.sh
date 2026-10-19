#!/usr/bin/env bash
set -euo pipefail
deadline=$((SECONDS + ${VERIFY_SECONDS:-300}))
while (( SECONDS < deadline )); do
  ok=1
  for domain in dhansetuhub.in www.dhansetuhub.in; do
    code=$(curl -L -sS -o /dev/null -w '%{http_code}' --max-time 15 "https://${domain}/api/health" || true)
    printf '%s %s %s\n' "$(date -Is)" "$domain" "$code"
    [[ "$code" == 200 ]] || ok=0
  done
  (( ok )) && exit 0
  sleep "${VERIFY_INTERVAL:-10}"
done
echo 'live verification timed out' >&2
exit 1
