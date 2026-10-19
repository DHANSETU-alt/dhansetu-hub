#!/bin/zsh
# Safe DhanSetu host diagnostics. It never changes macOS settings or touches
# unrelated processes. --relieve stops only known local development commands.
set -u

ROOT="/Users/apple/shakthi-os"
SERVICES="/Users/apple/shakthi-services"

print_report() {
  echo "DhanSetu Mac performance report"
  echo "root: $ROOT"
  echo "time: $(date '+%Y-%m-%dT%H:%M:%S%z')"
  echo
  uptime
  echo "\nMemory:"
  vm_stat | head -8
  echo "\nDisk:"
  df -h / "$ROOT" 2>/dev/null
  echo "\nProject processes (only known paths):"
  ps -axo pid,ppid,%cpu,%mem,etime,command | awk -v root="$ROOT" -v services="$SERVICES" 'index($0, root) || index($0, services) {print}' | head -80
  echo "\nListening ports:"
  for port in 3000 8787 3100 8888 20128; do
    lsof -nP -iTCP:$port -sTCP:LISTEN 2>/dev/null | tail -n +2 || true
  done
}

relieve() {
  echo "Stopping only known DhanSetu/Paperclip development processes..."
  # Match absolute paths/commands, never a broad name such as node or cargo.
  pkill -TERM -f "$ROOT/dashboard/node_modules/.bin/next" 2>/dev/null || true
  pkill -TERM -f "$ROOT/orchestrator/api.py" 2>/dev/null || true
  pkill -TERM -f "$SERVICES/paperclip.*dev-runner" 2>/dev/null || true
  pkill -TERM -f "$SERVICES/paperclip.*cargo build" 2>/dev/null || true
  sleep 2
  print_report
}

case "${1:-report}" in
  report) print_report ;;
  --relieve) relieve ;;
  *) echo "Usage: $0 [report|--relieve]" >&2; exit 2 ;;
esac
