#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT/docker-compose.selfhost.yml"
STORAGE_ROOT="${DHANSETU_STORAGE_ROOT:-/mnt/dhansetu-data}"

usage() {
  cat <<'EOF'
Usage: scripts/selfhost.sh <start|stop|restart|status|health|backup|restore-test|update>

The application refuses to start unless the configured storage path is a
mounted filesystem. `update` rebuilds the local image only; it never pulls,
pushes, changes DNS, or deploys externally.
EOF
}

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

case "${1:-}" in
  start)
    "$ROOT/scripts/storage-guard.sh"
    compose up -d --build
    ;;
  stop)
    compose down
    ;;
  restart)
    "$ROOT/scripts/storage-guard.sh"
    compose up -d --build --force-recreate
    ;;
  status)
    compose ps
    ;;
  health)
    curl --fail --silent --show-error "http://127.0.0.1:${DHANSETU_PORT:-3000}/api/health"
    printf '\n'
    ;;
  backup)
    "$ROOT/scripts/backup-local.sh"
    ;;
  restore-test)
    "$ROOT/ops/restore-test.sh"
    ;;
  update)
    "$ROOT/scripts/storage-guard.sh"
    compose build --pull=false
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
