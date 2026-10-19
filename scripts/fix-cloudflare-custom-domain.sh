#!/usr/bin/env bash
set -euo pipefail
: "${RENDER_API_KEY:?Set RENDER_API_KEY}"
SERVICE_ID="${RENDER_SERVICE_ID:-srv-danctvrbc2fs73dvv80g}"
for domain in dhansetuhub.in www.dhansetuhub.in; do
  code=$(curl --fail-with-body -sS -o /tmp/render-domain.json -w '%{http_code}' -X POST "https://api.render.com/v1/services/${SERVICE_ID}/custom-domains" -H "Authorization: Bearer $RENDER_API_KEY" -H 'Content-Type: application/json' --data "{\"name\":\"$domain\"}" || true)
  case "$code" in 200|201|409) echo "$domain: accepted ($code)";; *) cat /tmp/render-domain.json; exit 1;; esac
done
