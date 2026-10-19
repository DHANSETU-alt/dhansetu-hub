#!/bin/zsh
set -euo pipefail
ENV_FILE="/Users/apple/.config/dhansetu/host.env"
if [[ ! -r "$ENV_FILE" ]]; then
  echo "ERROR: missing $ENV_FILE; launchd will remain safely stopped." >&2
  exit 2
fi
set -a
source "$ENV_FILE"
set +a
exec /Users/apple/shakthi-os/scripts/dhansetu-host.sh "$@"
