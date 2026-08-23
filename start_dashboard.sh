#!/bin/bash
# Starts both servers the dashboard needs -- the API (orchestrator/api.py,
# :8787) and the Next.js dev server (dashboard/, :3000) -- in the
# background, logging to logs/*.log. Idempotent: re-running this while
# both are already up just reports that and does nothing.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

mkdir -p logs

start_if_needed() {
  local name="$1" port="$2" pidfile="$3" logfile="$4"
  shift 4
  if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "$name already running (pid $(cat "$pidfile"), http://127.0.0.1:$port)"
    return
  fi
  if lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "$name: port $port is already in use by another process -- not starting a second one."
    return
  fi
  nohup "$@" > "$logfile" 2>&1 &
  echo $! > "$pidfile"
  echo "$name started (pid $!, http://127.0.0.1:$port), logging to $logfile"
}

start_if_needed "API server" 8787 .api.pid logs/api.log \
  python3 -m orchestrator.api

start_if_needed "Dashboard" 3000 .dashboard.pid logs/dashboard.log \
  npm --prefix dashboard run dev

echo
echo "Waiting for both to come up..."
for i in 1 2 3 4 5 6 7 8 9 10; do
  api_ok=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8787/api/health 2>/dev/null || echo "000")
  dash_ok=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/ 2>/dev/null || echo "000")
  if [ "$api_ok" = "200" ] && [ "$dash_ok" = "200" ]; then
    echo "Both up. Dashboard: http://localhost:3000  API: http://127.0.0.1:8787"
    exit 0
  fi
  sleep 1
done
echo "Still starting -- check logs/api.log and logs/dashboard.log if this persists."
