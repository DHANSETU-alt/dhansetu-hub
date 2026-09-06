#!/bin/bash
set -euo pipefail

PROJECT_DIR="/home/blackboxops/ShakthiOS_v3.2"
export PATH="$PROJECT_DIR/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

cd "$PROJECT_DIR"
bash "$PROJECT_DIR/start_dashboard.sh"

for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8787/api/health >/dev/null 2>&1 \
    && curl -fsS http://127.0.0.1:3000/ >/dev/null 2>&1; then
    xdg-open http://127.0.0.1:3000/ >/dev/null 2>&1 &
    exit 0
  fi
  sleep 1
done

echo "SHAKTHI_OS did not become ready. Check $PROJECT_DIR/logs/."
exit 1
