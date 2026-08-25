#!/bin/bash
# Double-click to stop the API server and dashboard started by
# Start_Shakthi_OS.command.
cd "$(dirname "${BASH_SOURCE[0]}")"
./stop_dashboard.sh
echo
echo "Press any key to close this window..."
read -n 1
