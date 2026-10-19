#!/usr/bin/env bash
set -euo pipefail
service_id="${RENDER_SERVICE_ID:-srv-danctvrbc2fs73dvv80g}"
if [[ -z "${RENDER_API_KEY:-}" ]]; then
  cat > READY_TO_ADD_IN_RENDER.md <<EOF
# Ready to add in Render

Render Dashboard -> dhansetu-hub -> Settings -> Custom Domains -> Add Custom Domain.
Add `dhansetuhub.in`, then add `www.dhansetuhub.in`, and click Verify.

API payload:
POST https://api.render.com/v1/services/${service_id}/custom-domains
Authorization: Bearer \$RENDER_API_KEY
Content-Type: application/json
{"name":"dhansetuhub.in"}
EOF
  echo 'RENDER_API_KEY missing; wrote READY_TO_ADD_IN_RENDER.md'
  exit 2
fi
for domain in dhansetuhub.in www.dhansetuhub.in; do
  curl --fail-with-body -sS -X POST "https://api.render.com/v1/services/${service_id}/custom-domains" \
    -H "Authorization: Bearer $RENDER_API_KEY" -H 'Content-Type: application/json' \
    --data "{\"name\":\"$domain\"}"
done
