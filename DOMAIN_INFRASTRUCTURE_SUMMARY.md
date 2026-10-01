# Domain Infrastructure Summary: dhansetuhub.in Deployment

**Status:** Complete - Ready for Phase 3 Launch  
**Created:** 2026-10-01  
**Target Completion:** Phase 3 cutover  

---

## Executive Overview

This document summarizes the complete domain deployment infrastructure created for moving DhanSetu Hub from `dhansetuhub.workers.dev` (temporary) to `dhansetuhub.in` (production). The infrastructure includes DNS configuration, data migration procedures, monitoring setup, and comprehensive cutover procedures.

---

## Deliverables Checklist

### 1. DNS Configuration (`orchestrator/domain_config.py`)

**File:** `/Users/apple/shakthi-os/orchestrator/domain_config.py`

**Purpose:** Central configuration for DNS records, SSL/TLS settings, and email configuration

**Key Features:**
- Complete DNS record definitions (A, AAAA, MX, SPF, DMARC, TXT)
- Cloudflare API integration setup
- Security headers configuration (CSP, X-Frame-Options, etc.)
- SSL/TLS configuration with modern ciphers
- Email configuration templates
- DNS verification functions

**Usage:**
```bash
python orchestrator/domain_config.py
# Verifies current DNS configuration and SSL certificate

# Generate environment template
python -c "
from orchestrator.domain_config import generate_env_template
print(generate_env_template())
"

# Generate DNS verification script
python -c "
from orchestrator.domain_config import generate_dns_verification_script
print(generate_dns_verification_script())
" > verify_dns.sh
chmod +x verify_dns.sh
./verify_dns.sh
```

**Includes:**
- DNS record schemas with TTL values
- Cloudflare API token configuration
- SSL/TLS best practices (TLS 1.2+, modern ciphers)
- HSTS configuration with preload
- Email (Google Workspace/Gmail) MX records
- SPF and DMARC policy templates

### 2. Data Migration (`orchestrator/data_migration_dhansetuhub.py`)

**File:** `/Users/apple/shakthi-os/orchestrator/data_migration_dhansetuhub.py`

**Purpose:** Comprehensive data migration from workers.dev database to production dhansetuhub.in

**Key Features:**
- Database integrity verification before/after migration
- User data migration with referential integrity checks
- Razorpay transaction history migration (payments and refunds)
- Research content and insights migration
- Detailed migration reporting with error tracking
- Dry-run mode for safe testing

**Database Tables Created:**
- `razorpay_payments` - Payment history
- `razorpay_refunds` - Refund records
- `research_articles` - Published research content
- `research_insights` - Research insights and analysis

**Usage:**
```bash
# Dry-run test (no changes committed)
python orchestrator/data_migration_dhansetuhub.py

# OR with environment variables
DRY_RUN=true SOURCE_DB_PATH=shakthi.db TARGET_DB_PATH=shakthi_prod.db \
  python orchestrator/data_migration_dhansetuhub.py

# Production migration (commits changes)
DRY_RUN=false SOURCE_DB_PATH=shakthi.db TARGET_DB_PATH=shakthi_prod.db \
  python orchestrator/data_migration_dhansetuhub.py

# Check migration report
cat migration_report.json | jq .
```

**Generates:**
- `migration_report.json` - Detailed migration statistics and errors
- Automatic database integrity validation
- Referential integrity verification
- Migration timeline and duration tracking

### 3. Domain Monitoring (`orchestrator/domain_monitoring.py`)

**File:** `/Users/apple/shakthi-os/orchestrator/domain_monitoring.py`

**Purpose:** Continuous monitoring of domain health, SSL certificates, DNS, and HTTP status

**Key Features:**
- SSL certificate validation with expiry tracking
- DNS resolution verification (A, AAAA, MX, DNSSEC)
- HTTP/HTTPS status checks
- Redirect chain validation
- Uptime monitoring
- Automated health reports
- Monitoring alert generation

**Health Checks Performed:**
1. **SSL Certificate** - Valid, expiry date, issuer verification
2. **DNS Resolution** - A, AAAA, MX, DNSSEC records
3. **HTTP Status** - Response codes, redirect chains
4. **Redirect Chain** - Verify workers.dev → dhansetuhub.in redirection
5. **Uptime** - Domain availability and response time

**Usage:**
```bash
# Run all health checks
python orchestrator/domain_monitoring.py

# Or programmatically
from orchestrator.domain_monitoring import DomainMonitor

monitor = DomainMonitor("dhansetuhub.in")
checks = monitor.run_all_checks()
report = monitor.generate_health_report("health_report.json")

# Generate monitoring alerts
python -c "
from orchestrator.domain_monitoring import create_monitoring_alerts
create_monitoring_alerts()
"
```

**Generates:**
- `domain_health_report.json` - Detailed health check results
- `monitoring_alerts.yaml` - Alert rules for Datadog/New Relic

**Alert Rules Created:**
- SSL certificate expiry (30 days, 7 days, invalid)
- DNS resolution failures
- Domain unreachable (HTTP 5xx)
- High error rates
- Slow response times
- Domain down alerts

### 4. Domain Cutover Guide (`DOMAIN_CUTOVER_GUIDE.md`)

**File:** `/Users/apple/shakthi-os/DOMAIN_CUTOVER_GUIDE.md`

**Purpose:** Step-by-step guide for executing zero-downtime domain cutover

**Sections Included:**

1. **Pre-Cutover Checklist** (50+ items)
   - Infrastructure readiness
   - Configuration verification
   - Application testing
   - Security validation
   - Data integrity checks
   - Team readiness

2. **DNS Configuration**
   - Cloudflare zone setup
   - Registrar nameserver update
   - DNS record configuration (A, AAAA, MX, TXT, SPF, DMARC)
   - Verification procedures

3. **Pre-Cutover Preparation (24 hours before)**
   - TTL reduction (3600s → 300s)
   - Database backup and verification
   - API configuration staging
   - OAuth and Razorpay pre-configuration
   - Testing procedures
   - Communication plan

4. **Cutover Procedure (Atomic Switching)**
   - Phase 1: Final checks (T-1 hour)
   - Phase 2: Application deployment (T-0)
   - Phase 3: DNS cutover (T+0)
   - Phase 4: Verification (T+5 mins)

5. **Post-Cutover Validation (10-Point Checklist)**
   - DNS resolution verification
   - SSL certificate validation
   - HTTPS redirect verification
   - API health checks
   - OAuth functionality
   - Razorpay webhook verification
   - Email configuration
   - Database connectivity
   - Error rate monitoring
   - User traffic validation

6. **Rollback Procedure**
   - Rollback triggers (conditions for rollback)
   - Step-by-step rollback steps
   - Post-rollback analysis and investigation

7. **Post-Launch Monitoring**
   - Immediate monitoring (0-4 hours)
   - Extended monitoring (4-24 hours)
   - Key metrics and SLA targets
   - Alert configuration

8. **Troubleshooting Guide**
   - DNS not resolving
   - SSL certificate errors
   - API 404/500 errors
   - OAuth redirect loops
   - Email not sending
   - Razorpay webhook issues

9. **Communication Templates**
   - Pre-cutover announcement
   - Post-cutover celebration message

### 5. Environment Configuration Template

**Location:** Generated from `orchestrator/domain_config.py`

**Contents:**
```env
# Domain and API URLs
DOMAIN=dhansetuhub.in
API_URL=https://dhansetuhub.in
WORKERS_DOMAIN=dhansetuhub.workers.dev

# Cloudflare Configuration
CLOUDFLARE_API_TOKEN=[YOUR_TOKEN]
CLOUDFLARE_ACCOUNT_ID=[YOUR_ID]
CLOUDFLARE_ZONE_ID=[YOUR_ZONE]

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SUPPORT_EMAIL=support@dhansetuhub.in

# OAuth Configuration
GOOGLE_OAUTH_REDIRECT_URI=https://dhansetuhub.in/api/auth/google/callback

# Razorpay Configuration
RAZORPAY_WEBHOOK_URL=https://dhansetuhub.in/api/blackboxops/razorpay-webhook

# Security Settings
ENABLE_HTTPS=true
TLS_MIN_VERSION=1.2
```

---

## DNS Records Configuration

### Complete DNS Record Set

| Type | Name | Content | TTL | Proxied | Purpose |
|------|------|---------|-----|---------|---------|
| A | @ | Cloudflare IP | 300* | Yes | Root domain |
| AAAA | @ | Cloudflare IPv6 | 300* | Yes | IPv6 root |
| CNAME | www | dhansetuhub.in | 300* | Yes | www subdomain |
| MX | @ | aspmx.l.google.com (10) | 300* | No | Email routing |
| MX | @ | alt1.aspmx.l.google.com (20) | 300* | No | Email backup 1 |
| MX | @ | alt2.aspmx.l.google.com (30) | 300* | No | Email backup 2 |
| MX | @ | alt3.aspmx.l.google.com (40) | 300* | No | Email backup 3 |
| MX | @ | alt4.aspmx.l.google.com (50) | 300* | No | Email backup 4 |
| TXT | @ | v=spf1 include:_spf.google.com ~all | 300* | No | Email authentication |
| TXT | _dmarc | v=DMARC1; p=quarantine... | 300* | No | Domain authentication |

*TTL reduced to 300 seconds for 24 hours before cutover, then restored to 3600 for normal operation

---

## Configuration Files Created

### 1. Domain Configuration Module
- **Path:** `/Users/apple/shakthi-os/orchestrator/domain_config.py`
- **Size:** ~3.5KB
- **Functions:**
  - `verify_dns_configuration()` - Verify DNS setup
  - `verify_ssl_certificate()` - Check SSL status
  - `generate_env_template()` - Create .env file
  - `generate_dns_verification_script()` - Create verification bash script

### 2. Data Migration Module
- **Path:** `/Users/apple/shakthi-os/orchestrator/data_migration_dhansetuhub.py`
- **Size:** ~8.5KB
- **Classes:**
  - `MigrationReport` - Track migration progress
  - `DataMigrator` - Execute data migration

### 3. Domain Monitoring Module
- **Path:** `/Users/apple/shakthi-os/orchestrator/domain_monitoring.py`
- **Size:** ~7.2KB
- **Classes:**
  - `DomainMonitor` - Perform health checks
- **Functions:**
  - `create_monitoring_alerts()` - Generate alert YAML

### 4. Cutover Guide
- **Path:** `/Users/apple/shakthi-os/DOMAIN_CUTOVER_GUIDE.md`
- **Size:** ~25KB
- **Sections:** 9 major sections with step-by-step procedures

---

## Integration with Existing Systems

### Cloudflare Integration

**Current Setup:**
- Domain: `dhansetuhub.in` added to Cloudflare
- Nameservers: ns1.cloudflare.com, ns2.cloudflare.com
- SSL: Automatic certificate via Let's Encrypt
- Features: CDN, DDoS protection, WAF (available in paid plans)

**Configuration Points:**
```python
from orchestrator.domain_config import (
    CF_API_TOKEN,
    CF_ACCOUNT_ID,
    CF_ZONE_ID,
    DOMAIN,
    SSL_CONFIG,
    SECURITY_HEADERS
)
```

### Database Configuration

**Migration Tables:**
```sql
CREATE TABLE razorpay_payments (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    amount INTEGER NOT NULL,
    currency TEXT DEFAULT 'INR',
    status TEXT NOT NULL,
    order_id TEXT,
    receipt TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE razorpay_refunds (
    id TEXT PRIMARY KEY,
    payment_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    amount INTEGER NOT NULL,
    currency TEXT DEFAULT 'INR',
    status TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (payment_id) REFERENCES razorpay_payments(id)
);
```

### OAuth Configuration

**Google Console Updates:**
```
Authorized redirect URIs:
- https://dhansetuhub.in/api/auth/google/callback
- https://dhansetuhub.workers.dev/api/auth/google/callback (kept for rollback)
```

### Razorpay Webhook Configuration

**Webhook Endpoints:**
```
New:     https://dhansetuhub.in/api/blackboxops/razorpay-webhook
Backup:  https://dhansetuhub.workers.dev/api/blackboxops/razorpay-webhook
```

---

## Pre-Cutover Checklist Summary

### Infrastructure (8 items)
- [ ] Cloudflare account created
- [ ] Domain added to Cloudflare
- [ ] Nameservers noted
- [ ] SSL certificate provisioned
- [ ] Workers.dev backup verified
- [ ] Database backups created (2+ copies)
- [ ] Database integrity checks passing
- [ ] Backup storage tested

### Configuration (6 items)
- [ ] Environment variables prepared
- [ ] API keys secured
- [ ] Cloudflare API token configured
- [ ] Razorpay webhook URLs prepared
- [ ] Google OAuth URIs updated
- [ ] SMTP credentials verified

### Application Testing (8 items)
- [ ] SSL certificate chain verified
- [ ] All API endpoints tested
- [ ] Payment flow tested
- [ ] OAuth flow tested
- [ ] Email notifications tested
- [ ] CSV import/export tested
- [ ] Database queries tested
- [ ] Caching layer verified

### Security Verification (6 items)
- [ ] Security headers configured
- [ ] CORS headers verified
- [ ] Rate limiting configured
- [ ] DDoS protection enabled
- [ ] No hardcoded secrets found
- [ ] Vulnerability scan passed

### Data Integrity (5 items)
- [ ] Database schema verified
- [ ] User data backup completed
- [ ] Razorpay history exported
- [ ] Research content backup completed
- [ ] Referential integrity verified

### Team Readiness (6 items)
- [ ] On-call engineer assigned
- [ ] Communication channels ready
- [ ] Rollback authority identified
- [ ] Customer support briefed
- [ ] Status page prepared
- [ ] Monitoring enabled

**Total: 39 pre-cutover verification items**

---

## Cutover Timeline

### T-48 hours
- Final domain registration verification
- Cloudflare zone setup completion

### T-24 hours
- TTL reduction (3600s → 300s) for all DNS records
- Database backup and verification
- Staging environment testing with new domain

### T-12 hours
- API configuration prepared (.env staging)
- OAuth and integrations pre-configuration
- Team briefing and war room setup

### T-6 hours
- Integration test suite execution
- Database health check
- Domain connectivity test

### T-1 hour
- Final pre-cutover validation
- Backup verification
- Team ready check

### T-0 (Cutover Window)
- Application deployment (code/config)
- Nameserver update at registrar
- DNS propagation monitoring
- Service verification

### T+5 minutes
- 10-point validation checklist
- Error rate monitoring
- User traffic validation

### T+30 minutes
- First post-cutover report
- Continue monitoring

### T+4 hours
- Extended monitoring report
- Performance baseline established

### T+24 hours
- Full production verification
- Launch marked successful

---

## Monitoring & Alerts

### Continuous Monitoring
```bash
# Run every 5 minutes
python orchestrator/domain_monitoring.py

# Check certificate expiry daily
# Check DNS resolution every 10 minutes
# Check HTTP status every 5 minutes
```

### Alert Triggers
- SSL expiry < 30 days (CRITICAL)
- SSL expiry < 7 days (CRITICAL + PagerDuty)
- SSL certificate invalid (CRITICAL)
- DNS resolution failure (CRITICAL)
- Domain unreachable (CRITICAL + PagerDuty)
- HTTP 5xx errors (HIGH)
- Slow response time > 2s (MEDIUM)

### SLA Targets
- Uptime: 99.9% (monthly)
- Response time: < 200ms (p95)
- Error rate: < 0.1%
- SSL certificate: Valid, with 30+ days validity

---

## Rollback Procedure

**Quick Trigger:** If ANY validation check fails

**Rollback Steps:**
1. Stop services
2. Revert to workers.dev configuration
3. Restore database from pre-cutover backup
4. Restart services
5. Verify on workers.dev
6. Investigate root cause

**Estimated Rollback Time:** 10-15 minutes

---

## Post-Launch Monitoring

### 0-4 Hours (Intensive)
- Continuous error log monitoring
- API response time tracking
- User transaction monitoring
- Email delivery tracking

### 4-24 Hours (Standard)
- Hourly health checks
- Daily report generation
- Performance baseline verification
- No regressions detected

### After 24 Hours
- Daily health check emails
- Weekly performance reports
- Monthly SLA verification

---

## Success Criteria

**Launch is successful if:**
1. ✓ All 10 post-cutover validation checks pass
2. ✓ Error rate < 0.1% in first 4 hours
3. ✓ API response time < 200ms (p95)
4. ✓ No customer-impacting errors
5. ✓ OAuth and payments working
6. ✓ Email delivery working
7. ✓ Monitoring alerts active
8. ✓ Team notified of completion

---

## Next Steps for Execution

### Week 1: Final Preparation
1. Review cutover guide with entire team
2. Verify all DNS records in Cloudflare
3. Complete pre-cutover checklist
4. Schedule cutover window

### Week 2: Cutover Execution
1. Execute pre-cutover procedures (24 hours before)
2. Execute cutover procedure
3. Validate post-cutover
4. Monitor intensive (0-4 hours)

### Week 3: Monitoring & Handoff
1. Extended monitoring (4-24 hours)
2. Validate SLA targets
3. Generate post-launch report
4. Update documentation

---

## Support & Escalation

**For Issues During Cutover:**
- Slack channel: #dhansetuhub-domain-cutover
- On-call engineer: [Name] - [Phone]
- Escalation: [Engineering Lead]

**For Pre/Post Cutover Questions:**
- Docs: `/Users/apple/shakthi-os/DOMAIN_CUTOVER_GUIDE.md`
- Config: `/Users/apple/shakthi-os/orchestrator/domain_config.py`
- Monitoring: `/Users/apple/shakthi-os/orchestrator/domain_monitoring.py`

---

## Document Control

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-10-01 | Initial infrastructure created |
| | | - DNS configuration module |
| | | - Data migration module |
| | | - Domain monitoring module |
| | | - Comprehensive cutover guide |
| | | - Monitoring alert templates |

**Approved by:** [Engineering Lead]  
**Last Review:** 2026-10-01  
**Next Review:** After successful cutover  

---

**Status:** ✅ Complete - Ready for Phase 3 Execution
