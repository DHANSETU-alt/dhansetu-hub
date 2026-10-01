#!/bin/bash
# Double-click this file in Finder (or on the Desktop) to start everything --
# API server, dashboard, and it opens Chrome to the dashboard automatically.
# Nothing else to type. Closing this Terminal window does NOT stop the
# servers (they're detached background processes) -- use
# Stop_Shakthi_OS.command for that.
SHAKTHI_ROOT="/Users/apple/shakthi-os"
cd "$SHAKTHI_ROOT"

echo "Starting SHAKTHI OS..."
./start_dashboard.sh

echo
echo "Opening dashboard in Chrome..."
open -a "Google Chrome" "http://localhost:3000" 2>/dev/null || open "http://localhost:3000"

echo "Opening Shakthi_OS1.0 active work list..."
open "$SHAKTHI_ROOT/tasks/Shakthi_OS1.0.md"

echo
echo "SHAKTHI OS is running. You can close this window -- the servers keep running."
echo "To stop everything later, double-click Stop_Shakthi_OS.command."
