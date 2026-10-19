#!/usr/bin/env bash
set -euo pipefail
VERIFY_SECONDS="${VERIFY_SECONDS:-300}" VERIFY_INTERVAL="${VERIFY_INTERVAL:-10}" bash "$(dirname "$0")/verify-live.sh"
