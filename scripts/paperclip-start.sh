#!/bin/zsh
set -euo pipefail
ENV_FILE="/Users/apple/.config/dhansetu/host.env"
if [[ ! -r "$ENV_FILE" ]]; then
  echo "ERROR: missing $ENV_FILE; Paperclip will remain stopped." >&2
  exit 2
fi
set -a
source "$ENV_FILE"
set +a
/Users/apple/shakthi-os/scripts/dhansetu-host.sh check-storage >/dev/null

PAPERCLIP_HOME="$DHANSETU_SSD_ROOT/data/paperclip"
PAPERCLIP_DATA_DIR="$PAPERCLIP_HOME"
PAPERCLIP_PORT="${PAPERCLIP_PORT:-3100}"
export PAPERCLIP_HOME PAPERCLIP_DATA_DIR PAPERCLIP_PORT
cd /Users/apple/shakthi-services/paperclip
exec /Users/apple/shakthi-services/bin/pnpm --filter @paperclipai/server start
