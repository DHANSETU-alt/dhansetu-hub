#!/bin/bash
# Stops what start_dashboard.sh started, by PID file. Safe to run even if
# one or both aren't running.
cd "$(dirname "${BASH_SOURCE[0]}")"

stop_one() {
  local name="$1" pidfile="$2"
  if [ -f "$pidfile" ]; then
    pid="$(cat "$pidfile")"
    if kill -0 "$pid" 2>/dev/null; then
      pkill -P "$pid" 2>/dev/null || true  # npm forwards to `next dev`/etc. inconsistently -- also kill its direct children
      kill "$pid"
      echo "$name stopped (pid $pid)"
    else
      echo "$name: pid $pid from $pidfile is not running"
    fi
    rm -f "$pidfile"
  else
    echo "$name: no pidfile ($pidfile) -- not started by start_dashboard.sh, or already stopped"
  fi
}

stop_one "API server" .api.pid
stop_one "Dashboard" .dashboard.pid
