#!/bin/bash
# SHAKTHI_OS Phase 2 SSD Startup Script
# =====================================
#
# Orchestrates complete startup sequence with SSD integration.
#
# Usage:
#   ./orchestrator/startup.sh [--verify-only] [--rollback] [--no-monitoring]
#
# Options:
#   --verify-only      Run verification steps only (no startup)
#   --rollback         Rollback to previous database configuration
#   --no-monitoring    Skip SSD health monitoring setup
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# SSD configuration
SSD_MOUNT_POINT="/Volumes/CLAUDFLAIR_SSD"
SSD_DB_PATH="${SSD_MOUNT_POINT}/shakthi-db/shakthi.db"
SSD_LOGS_PATH="${SSD_MOUNT_POINT}/logs"
SSD_CACHE_PATH="${SSD_MOUNT_POINT}/cache"

# Export for Python
export SHAKTHI_DB_PATH="${SSD_DB_PATH}"

# Parse arguments
VERIFY_ONLY=false
ROLLBACK_MODE=false
NO_MONITORING=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --verify-only)
            VERIFY_ONLY=true
            shift
            ;;
        --rollback)
            ROLLBACK_MODE=true
            shift
            ;;
        --no-monitoring)
            NO_MONITORING=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# ==============================================================================
# ROLLBACK MODE
# ==============================================================================

if [ "$ROLLBACK_MODE" = true ]; then
    log_info "ROLLBACK MODE: Restoring previous database configuration..."

    if [ -f "${SSD_DB_PATH}/../.rollback_migration.sh" ]; then
        log_info "Executing rollback script..."
        bash "${SSD_DB_PATH}/../.rollback_migration.sh"
        log_success "Rollback completed"
        exit 0
    else
        log_error "Rollback script not found at ${SSD_DB_PATH}/../.rollback_migration.sh"
        exit 1
    fi
fi

# ==============================================================================
# PRE-FLIGHT CHECKS
# ==============================================================================

log_info "=========================================="
log_info "SHAKTHI_OS Phase 2 SSD Startup Sequence"
log_info "=========================================="
echo ""

log_info "Pre-flight Checks"
log_info "-----------------"

# Check 1: SSD mounted
if [ -d "${SSD_MOUNT_POINT}" ]; then
    log_success "SSD mounted at ${SSD_MOUNT_POINT}"
else
    log_error "SSD not mounted at ${SSD_MOUNT_POINT}"
    log_warning "Attempting to mount SSD..."
    diskutil mount "${SSD_MOUNT_POINT}" 2>/dev/null || {
        log_error "Failed to mount SSD. Aborting."
        exit 1
    }
    log_success "SSD mounted successfully"
fi

# Check 2: SSD directories exist
if [ -d "${SSD_DB_PATH%/*}" ]; then
    log_success "SSD database directory exists"
else
    log_warning "SSD database directory missing, creating..."
    mkdir -p "${SSD_DB_PATH%/*}" || {
        log_error "Failed to create database directory"
        exit 1
    }
fi

# Check 3: Database file exists
if [ -f "${SSD_DB_PATH}" ]; then
    log_success "Database file found at ${SSD_DB_PATH}"
else
    log_error "Database file not found at ${SSD_DB_PATH}"
    log_warning "Has database migration completed? See: $PROJECT_ROOT/SSD_MIGRATION_GUIDE.md"
    exit 1
fi

# Check 4: Disk space
DISK_USAGE=$(df "${SSD_MOUNT_POINT}" | awk 'NR==2 {print $4}')
DISK_USAGE_MB=$((DISK_USAGE / 1024))

if [ "$DISK_USAGE_MB" -gt 500 ]; then
    log_success "Disk space adequate: ${DISK_USAGE_MB}MB free"
else
    log_warning "Low disk space: ${DISK_USAGE_MB}MB free (threshold: 500MB)"
fi

echo ""

# ==============================================================================
# VERIFICATION ONLY MODE
# ==============================================================================

if [ "$VERIFY_ONLY" = true ]; then
    log_info "Verification complete (--verify-only mode)"
    exit 0
fi

# ==============================================================================
# PYTHON STARTUP SEQUENCE
# ==============================================================================

log_info "Running Startup Sequence"
log_info "------------------------"

cd "$PROJECT_ROOT"

python3 << 'PYTHON_EOF'
import sys
import os
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from orchestrator.startup import run_startup

    logger.info("Starting Python startup sequence...")
    success, report = run_startup()

    # Print report
    print(json.dumps(report, indent=2, default=str))

    if not success:
        sys.exit(1)

except Exception as e:
    logger.error(f"Startup failed: {e}", exc_info=True)
    sys.exit(1)

PYTHON_EOF

STARTUP_STATUS=$?

if [ $STARTUP_STATUS -ne 0 ]; then
    log_error "Python startup sequence failed"
    exit 1
fi

# ==============================================================================
# HEALTH CHECK
# ==============================================================================

echo ""
log_info "Post-Startup Health Check"
log_info "-------------------------"

# Check database connectivity
python3 << 'PYTHON_EOF'
import sqlite3
from pathlib import Path

db_path = Path(os.environ.get("SHAKTHI_DB_PATH"))

try:
    conn = sqlite3.connect(str(db_path), timeout=5)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
    table_count = cursor.fetchone()[0]
    conn.close()

    print(f"✓ Database accessible ({table_count} tables)")
except Exception as e:
    print(f"✗ Database connectivity failed: {e}")
    sys.exit(1)
PYTHON_EOF

if [ $? -eq 0 ]; then
    log_success "Health check passed"
else
    log_error "Health check failed"
    exit 1
fi

# ==============================================================================
# SETUP MONITORING
# ==============================================================================

if [ "$NO_MONITORING" = false ]; then
    log_info "Initializing SSD Health Monitoring"

    python3 << 'PYTHON_EOF'
from orchestrator.ssd_health import setup_ssd_monitoring
setup_ssd_monitoring(check_interval_seconds=60)
print("✓ SSD monitoring initialized")
PYTHON_EOF

    if [ $? -eq 0 ]; then
        log_success "Monitoring initialized"
    else
        log_warning "Failed to initialize monitoring (non-critical)"
    fi
fi

# ==============================================================================
# STARTUP COMPLETE
# ==============================================================================

echo ""
log_info "=========================================="
log_success "SHAKTHI_OS Startup Complete"
log_info "=========================================="
echo ""
echo "Database: $SSD_DB_PATH"
echo "Logs:     $SSD_LOGS_PATH"
echo "Cache:    $SSD_CACHE_PATH"
echo ""
log_info "Ready for production use"
echo ""

exit 0
