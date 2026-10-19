#!/bin/zsh
set -euo pipefail
ROOT="/Users/apple/shakthi-os"
ENV_FILE="/Users/apple/.config/dhansetu/host.env"
if [[ ! -r "$ENV_FILE" ]]; then
  echo "ERROR: missing $ENV_FILE; API will remain stopped." >&2
  exit 2
fi
set -a
source "$ENV_FILE"
set +a
exec "$ROOT/scripts/dhansetu-host.sh" check-storage >/dev/null
cd "$ROOT"
exec /usr/local/bin/python3 -m orchestrator.api
