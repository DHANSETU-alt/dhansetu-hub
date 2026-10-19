#!/bin/bash
# Domain Infrastructure Verification Script
# Validates all dhansetuhub.in infrastructure components
# Run before cutover to ensure everything is ready

set -e

DOMAIN="dhansetuhub.in"
WORKERS_DOMAIN="dhansetuhub.workers.dev"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
REPORT_FILE="domain_verification_report_${TIMESTAMP}.txt"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_SKIPPED=0

# Functions
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "$REPORT_FILE"
}

success() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "$REPORT_FILE"
    ((CHECKS_PASSED++))
}

failure() {
    echo -e "${RED}✗${NC} $1" | tee -a "$REPORT_FILE"
    ((CHECKS_FAILED++))
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1" | tee -a "$REPORT_FILE"
}

skip() {
    echo -e "${YELLOW}~${NC} $1 (skipped)" | tee -a "$REPORT_FILE"
    ((CHECKS_SKIPPED++))
}

# Header
echo "========================================" | tee "$REPORT_FILE"
echo "Domain Infrastructure Verification" | tee -a "$REPORT_FILE"
echo "Domain: $DOMAIN" | tee -a "$REPORT_FILE"
echo "Timestamp: $TIMESTAMP" | tee -a "$REPORT_FILE"
echo "========================================" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# Section: Configuration Files
log "Section 1: Configuration Files"
echo "================================" >> "$REPORT_FILE"

if [ -f "orchestrator/domain_config.py" ]; then
    success "Domain configuration module exists"
else
    failure "Domain configuration module missing"
fi

if [ -f "orchestrator/data_migration_dhansetuhub.py" ]; then
    success "Data migration module exists"
else
    failure "Data migration module missing"
fi

if [ -f "orchestrator/domain_monitoring.py" ]; then
    success "Domain monitoring module exists"
else
    failure "Domain monitoring module missing"
fi

if [ -f "DOMAIN_CUTOVER_GUIDE.md" ]; then
    success "Cutover guide exists"
else
    failure "Cutover guide missing"
fi

if [ -f "DOMAIN_INFRASTRUCTURE_SUMMARY.md" ]; then
    success "Infrastructure summary exists"
else
    failure "Infrastructure summary missing"
fi

echo "" | tee -a "$REPORT_FILE"

# Section: Python Dependencies
log "Section 2: Python Dependencies"
echo "================================" >> "$REPORT_FILE"

if python3 -c "import sqlite3" 2>/dev/null; then
    success "sqlite3 available"
else
    failure "sqlite3 not available"
fi

if python3 -c "import json" 2>/dev/null; then
    success "json available"
else
    failure "json not available"
fi

if python3 -c "import subprocess" 2>/dev/null; then
    success "subprocess available"
else
    failure "subprocess not available"
fi

echo "" | tee -a "$REPORT_FILE"

# Section: Database Verification
log "Section 3: Database Configuration"
echo "================================" >> "$REPORT_FILE"

DB_PATH="${SHAKTHI_DB_PATH:-shakthi.db}"

if [ -f "$DB_PATH" ]; then
    success "Database file exists at $DB_PATH"

    # Check database integrity
    if sqlite3 "$DB_PATH" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
        success "Database integrity check passed"
    else
        failure "Database integrity check failed"
    fi

    # Check if users table exists
    if sqlite3 "$DB_PATH" ".tables" 2>/dev/null | grep -q "users"; then
        success "Users table exists"
    else
        warning "Users table not found (may be created during migration)"
    fi
else
    failure "Database file not found at $DB_PATH"
fi

echo "" | tee -a "$REPORT_FILE"

# Section: DNS Configuration
log "Section 4: DNS Configuration"
echo "================================" >> "$REPORT_FILE"

# Check dig command
if ! command -v dig &> /dev/null; then
    skip "dig command (required for DNS checks)"
else
    # Check nameservers
    log "Checking nameservers..."
    NS_RESULT=$(dig NS "$DOMAIN" +short 2>/dev/null || echo "")

    if echo "$NS_RESULT" | grep -q "cloudflare"; then
        success "Cloudflare nameservers configured"
    else
        warning "Cloudflare nameservers not yet active (may be pending registrar update)"
        echo "  Current nameservers: $NS_RESULT" | tee -a "$REPORT_FILE"
    fi

    # Check A record
    log "Checking A records..."
    A_RESULT=$(dig A "$DOMAIN" +short @ns1.cloudflare.com 2>/dev/null || echo "")

    if [ -n "$A_RESULT" ]; then
        success "A record configured: $A_RESULT"
    else
        warning "A record not yet configured in Cloudflare"
    fi

    # Check MX records
    log "Checking MX records..."
    MX_RESULT=$(dig MX "$DOMAIN" +short @ns1.cloudflare.com 2>/dev/null || echo "")

    if echo "$MX_RESULT" | grep -q "google.com"; then
        success "MX records point to Google (Gmail)"
    else
        warning "MX records not yet configured"
    fi
fi

echo "" | tee -a "$REPORT_FILE"

# Section: SSL/TLS Configuration
log "Section 5: SSL/TLS Configuration"
echo "================================" >> "$REPORT_FILE"

if ! command -v openssl &> /dev/null; then
    skip "openssl command (required for SSL checks)"
else
    log "Checking SSL certificate..."

    SSL_OUTPUT=$(echo | openssl s_client -connect "$DOMAIN:443" -showcerts 2>/dev/null || echo "")

    if echo "$SSL_OUTPUT" | grep -q "Verify return code: 0"; then
        success "SSL certificate is valid"

        # Extract expiry date
        EXPIRY=$(echo "$SSL_OUTPUT" | grep "notAfter=" | cut -d'=' -f2)
        success "Certificate expires: $EXPIRY"
    else
        warning "SSL certificate not yet valid (may be pending DNS propagation)"
    fi
fi

echo "" | tee -a "$REPORT_FILE"

# Section: HTTP/HTTPS Reachability
log "Section 6: HTTP/HTTPS Reachability"
echo "================================" >> "$REPORT_FILE"

if ! command -v curl &> /dev/null; then
    skip "curl command (required for HTTP checks)"
else
    log "Testing HTTPS connectivity..."

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -L "https://$DOMAIN/" 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" != "000" ]; then
        success "HTTPS responsive (HTTP $HTTP_CODE)"
    else
        warning "HTTPS not yet responsive (may be pending DNS or deployment)"
    fi

    log "Testing HTTP → HTTPS redirect..."

    REDIRECT=$(curl -s -o /dev/null -w "%{redirect_url}" "http://$DOMAIN/" 2>/dev/null || echo "")

    if echo "$REDIRECT" | grep -q "https"; then
        success "HTTP redirects to HTTPS"
    else
        warning "HTTP redirect not yet configured"
    fi
fi

echo "" | tee -a "$REPORT_FILE"

# Section: Environment Configuration
log "Section 7: Environment Configuration"
echo "================================" >> "$REPORT_FILE"

# Check if environment variables are set
if [ -n "$CLOUDFLARE_API_TOKEN" ]; then
    success "CLOUDFLARE_API_TOKEN is set"
else
    warning "CLOUDFLARE_API_TOKEN not set (required for cutover)"
fi

if [ -n "$CLOUDFLARE_ZONE_ID" ]; then
    success "CLOUDFLARE_ZONE_ID is set"
else
    warning "CLOUDFLARE_ZONE_ID not set (required for cutover)"
fi

# Check .env files
if [ -f ".env" ]; then
    success ".env file exists"

    if grep -q "DOMAIN=dhansetuhub.in" .env 2>/dev/null; then
        success ".env contains dhansetuhub.in configuration"
    else
        warning ".env does not contain dhansetuhub.in configuration"
    fi
else
    warning ".env file not found"
fi

if [ -f ".env.example" ]; then
    success ".env.example exists"
else
    warning ".env.example not found"
fi

echo "" | tee -a "$REPORT_FILE"

# Section: Git Status
log "Section 8: Git Status"
echo "================================" >> "$REPORT_FILE"

if ! command -v git &> /dev/null; then
    skip "git command (required for version control checks)"
else
    # Check for uncommitted changes
    if git status --porcelain 2>/dev/null | grep -q "^"; then
        warning "Uncommitted changes in repository"
        echo "  Run 'git status' to see details" | tee -a "$REPORT_FILE"
    else
        success "Repository is clean (no uncommitted changes)"
    fi

    # Get current branch
    BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    echo "  Current branch: $BRANCH" | tee -a "$REPORT_FILE"
fi

echo "" | tee -a "$REPORT_FILE"

# Section: Pre-Cutover Checklist Status
log "Section 9: Pre-Cutover Status"
echo "================================" >> "$REPORT_FILE"

echo "Infrastructure readiness:" | tee -a "$REPORT_FILE"
echo "  Configuration modules: $([ $CHECKS_PASSED -ge 5 ] && echo 'OK' || echo 'INCOMPLETE')" | tee -a "$REPORT_FILE"
echo "  Database setup: $([ -f "$DB_PATH" ] && echo 'OK' || echo 'MISSING')" | tee -a "$REPORT_FILE"
echo "  Cloudflare DNS: $(dig NS "$DOMAIN" +short 2>/dev/null | grep -q cloudflare && echo 'OK' || echo 'PENDING')" | tee -a "$REPORT_FILE"
echo "  SSL Certificate: $(echo | openssl s_client -connect "$DOMAIN:443" 2>/dev/null | grep -q "Verify return code: 0" && echo 'OK' || echo 'PENDING')" | tee -a "$REPORT_FILE"

echo "" | tee -a "$REPORT_FILE"

# Summary
echo "========================================" | tee -a "$REPORT_FILE"
echo "Verification Summary" | tee -a "$REPORT_FILE"
echo "========================================" | tee -a "$REPORT_FILE"

TOTAL=$((CHECKS_PASSED + CHECKS_FAILED + CHECKS_SKIPPED))

echo "Checks passed:  $CHECKS_PASSED" | tee -a "$REPORT_FILE"
echo "Checks failed:  $CHECKS_FAILED" | tee -a "$REPORT_FILE"
echo "Checks skipped: $CHECKS_SKIPPED" | tee -a "$REPORT_FILE"
echo "Total:          $TOTAL" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# Determine readiness
if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}Status: READY FOR CUTOVER${NC}" | tee -a "$REPORT_FILE"
    READINESS="READY"
elif [ $CHECKS_FAILED -le 3 ]; then
    echo -e "${YELLOW}Status: MOSTLY READY (Minor issues found)${NC}" | tee -a "$REPORT_FILE"
    READINESS="MOSTLY_READY"
else
    echo -e "${RED}Status: NOT READY (Multiple issues found)${NC}" | tee -a "$REPORT_FILE"
    READINESS="NOT_READY"
fi

echo "" | tee -a "$REPORT_FILE"
echo "Next steps:" | tee -a "$REPORT_FILE"

if [ "$READINESS" = "READY" ]; then
    echo "1. Review DOMAIN_CUTOVER_GUIDE.md" | tee -a "$REPORT_FILE"
    echo "2. Schedule cutover window with team" | tee -a "$REPORT_FILE"
    echo "3. Execute cutover using documented procedures" | tee -a "$REPORT_FILE"
elif [ "$READINESS" = "MOSTLY_READY" ]; then
    echo "1. Fix remaining issues (see failures above)" | tee -a "$REPORT_FILE"
    echo "2. Re-run this verification script" | tee -a "$REPORT_FILE"
    echo "3. Then proceed with cutover" | tee -a "$REPORT_FILE"
else
    echo "1. Address all failures listed above" | tee -a "$REPORT_FILE"
    echo "2. Verify configuration is correct" | tee -a "$REPORT_FILE"
    echo "3. Re-run this verification script" | tee -a "$REPORT_FILE"
    echo "4. DO NOT proceed with cutover until READY" | tee -a "$REPORT_FILE"
fi

echo "" | tee -a "$REPORT_FILE"
echo "Report saved to: $REPORT_FILE" | tee -a "$REPORT_FILE"
echo "========================================" | tee -a "$REPORT_FILE"

# Exit with appropriate status
if [ $CHECKS_FAILED -eq 0 ]; then
    exit 0
else
    exit 1
fi
