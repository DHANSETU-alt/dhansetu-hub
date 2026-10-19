# dhansetuhub.in Domain Deployment - Quick Reference

**Status:** ✅ Complete - Ready for Phase 3 Launch  
**Domain:** dhansetuhub.in  
**Current Location:** dhansetuhub.workers.dev (temporary)  
**Target Launch:** Phase 3 production cutover

---

## Quick Navigation

| What | Where | Purpose |
|------|-------|---------|
| **Cutover Steps** | [DOMAIN_CUTOVER_GUIDE.md](./DOMAIN_CUTOVER_GUIDE.md) | Step-by-step procedures for domain migration |
| **Infrastructure Summary** | [DOMAIN_INFRASTRUCTURE_SUMMARY.md](./DOMAIN_INFRASTRUCTURE_SUMMARY.md) | Complete overview of all components |
| **DNS Config** | [orchestrator/domain_config.py](./orchestrator/domain_config.py) | DNS records, SSL/TLS, security headers |
| **Data Migration** | [orchestrator/data_migration_dhansetuhub.py](./orchestrator/data_migration_dhansetuhub.py) | Database, Razorpay, content migration |
| **Monitoring** | [orchestrator/domain_monitoring.py](./orchestrator/domain_monitoring.py) | Health checks, alerts, reporting |
| **Verification** | [verify_domain_infrastructure.sh](./verify_domain_infrastructure.sh) | Pre-cutover checklist automation |

---

## Pre-Cutover: Quick Checklist (24 hours before)

```bash
# 1. Run verification script
bash verify_domain_infrastructure.sh

# 2. Create database backup
sqlite3 shakthi.db ".backup 'shakthi_backup_$(date +%Y%m%d_%H%M%S).db'"

# 3. Verify DNS is ready
dig dhansetuhub.in @ns1.cloudflare.com +short A

# 4. Check SSL certificate
echo | openssl s_client -connect dhansetuhub.in:443 -showcerts

# 5. Test API on staging
curl -I https://dhansetuhub.in/health

# 6. Run domain monitoring
python orchestrator/domain_monitoring.py

# 7. Reduce TTL in Cloudflare (→ 300 seconds)
# Dashboard > DNS > Edit each record

# 8. Verify OAuth config
# Google Cloud Console: Add https://dhansetuhub.in/api/auth/google/callback

# 9. Verify Razorpay webhooks
# Razorpay Dashboard: Add https://dhansetuhub.in/api/blackboxops/razorpay-webhook
```

---

## Cutover: Critical Commands (Execution Day)

```bash
# T-1 hour: Final checks
bash verify_domain_infrastructure.sh

# T-0: Deploy application (code only)
wrangler publish --env production

# T+0: Verify nameservers updated (may take 5-30 mins)
watch -n 5 'dig NS dhansetuhub.in +short'

# T+5 mins: Post-cutover validation
curl -v https://dhansetuhub.in
echo | openssl s_client -connect dhansetuhub.in:443 -showcerts
curl https://dhansetuhub.in/health

# T+30 mins: Generate validation report
python orchestrator/domain_monitoring.py > health_check_post_cutover.txt
```

---

## Monitoring: Post-Launch (0-24 hours)

```bash
# Watch continuously
python orchestrator/domain_monitoring.py

# Or with cron (every 5 minutes)
*/5 * * * * cd /path/to/shakthi-os && python orchestrator/domain_monitoring.py >> monitoring.log

# Generate reports
python -c "
from orchestrator.domain_monitoring import DomainMonitor
monitor = DomainMonitor('dhansetuhub.in')
checks = monitor.run_all_checks()
monitor.generate_health_report('health_report.json')
"
```

---

## Files Created

### 1. Configuration Modules (Orchestrator)

**`orchestrator/domain_config.py`** (534 lines)
- DNS record definitions (A, AAAA, MX, TXT, SPF, DMARC)
- SSL/TLS configuration (TLS 1.2+, HSTS, ciphers)
- Security headers (CSP, X-Frame-Options, etc.)
- Email configuration (SMTP, support contact)
- Verification functions for DNS and SSL
- Environment template generator
- DNS verification script generator

**`orchestrator/data_migration_dhansetuhub.py`** (536 lines)
- MigrationReport dataclass for tracking progress
- DataMigrator class with methods:
  - Database integrity verification
  - User data migration
  - Razorpay transaction history migration
  - Research content/insights migration
  - Referential integrity validation
  - Migration report generation
- Creates database tables for Razorpay and research data
- Full error tracking and logging

**`orchestrator/domain_monitoring.py`** (451 lines)
- DomainMonitor class with health checks:
  - SSL certificate validation
  - DNS resolution verification
  - HTTP/HTTPS status checks
  - Redirect chain validation
  - Uptime monitoring
- Report generation functions
- Monitoring alert YAML generator
- Supports continuous monitoring

### 2. Documentation

**`DOMAIN_CUTOVER_GUIDE.md`** (750+ lines)
- Pre-cutover checklist (39 items)
- DNS configuration steps
- 24-hour preparation procedures
- Atomic cutover procedure (4 phases)
- 10-point post-cutover validation
- Rollback procedures with triggers
- Post-launch monitoring (0-4 hours, 4-24 hours)
- Comprehensive troubleshooting guide
- Communication templates
- Sign-off forms

**`DOMAIN_INFRASTRUCTURE_SUMMARY.md`** (520+ lines)
- Executive overview
- Complete deliverables checklist
- DNS record configuration table
- Integration points with existing systems
- Pre-cutover checklist (39 items)
- Cutover timeline (T-48 to T+24 hours)
- Monitoring and alert configuration
- Success criteria
- Support and escalation contacts

**`DOMAIN_DEPLOYMENT_README.md`** (this file)
- Quick reference guide
- File navigation table
- Quick checklists
- Critical cutover commands
- Post-launch monitoring procedures

### 3. Automation

**`verify_domain_infrastructure.sh`** (Executable, 340+ lines)
- Automated pre-cutover verification
- 9 verification sections:
  1. Configuration files
  2. Python dependencies
  3. Database verification
  4. DNS configuration
  5. SSL/TLS setup
  6. HTTP/HTTPS reachability
  7. Environment configuration
  8. Git status
  9. Pre-cutover readiness status
- Colored output and logging
- Summary report generation
- Exit status for automation

---

## Cutover Timeline

| Time | Action | Status |
|------|--------|--------|
| T-48h | Domain registration + Cloudflare setup | ✅ Complete |
| T-24h | TTL reduction + backup + OAuth prep | Manual |
| T-12h | API staging + integration test | Manual |
| T-6h  | Pre-cutover validation | Manual |
| T-1h  | Final checks + team ready | Manual |
| T-0   | Deploy app + update DNS | Manual |
| T+5m  | Validate all 10 checks | Manual |
| T+30m | First report to team | Automated |
| T+4h  | Extended monitoring starts | Automated |
| T+24h | Launch success verification | Automated |

---

## Environment Variables Required

```env
# Cloudflare
CLOUDFLARE_API_TOKEN=<your_token>
CLOUDFLARE_ACCOUNT_ID=<your_id>
CLOUDFLARE_ZONE_ID=<zone_id_for_dhansetuhub.in>

# Domain URLs
DOMAIN=dhansetuhub.in
API_URL=https://dhansetuhub.in
WORKERS_DOMAIN=dhansetuhub.workers.dev  # Keep for rollback

# OAuth (Google)
GOOGLE_OAUTH_REDIRECT_URI=https://dhansetuhub.in/api/auth/google/callback

# Razorpay
RAZORPAY_WEBHOOK_URL=https://dhansetuhub.in/api/blackboxops/razorpay-webhook
RAZORPAY_WEBHOOK_SECRET=<your_secret>

# Email (Gmail/Google Workspace)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SUPPORT_EMAIL=support@dhansetuhub.in

# Database
DATABASE_URL=sqlite:///shakthi.db

# Security
ENABLE_HTTPS=true
TLS_MIN_VERSION=1.2
```

---

## DNS Records at Cloudflare

| Type | Name | Content | TTL | Proxied |
|------|------|---------|-----|---------|
| A | @ | [Cloudflare IP] | 300 | Yes |
| AAAA | @ | [Cloudflare IPv6] | 300 | Yes |
| MX | @ | aspmx.l.google.com | 300 | No |
| TXT | @ | v=spf1 include:_spf.google.com ~all | 300 | No |
| TXT | _dmarc | v=DMARC1; p=quarantine... | 300 | No |

**Note:** TTL set to 300 seconds (5 mins) for 24 hours before/after cutover. Restore to 3600 after verification.

---

## Key Contact Points

### OAuth Configuration
- **Service:** Google Cloud Console
- **Update:** Add `https://dhansetuhub.in/api/auth/google/callback` to Authorized redirect URIs
- **Keep:** `https://dhansetuhub.workers.dev/api/auth/google/callback` (for rollback)

### Razorpay Webhooks
- **Service:** Razorpay Dashboard
- **Add:** `https://dhansetuhub.in/api/blackboxops/razorpay-webhook`
- **Keep:** Old endpoint active (for rollback)

### Email Configuration
- **MX Records:** Google Workspace (Gmail)
- **SPF:** Configure in Cloudflare TXT record
- **DMARC:** Add `_dmarc.dhansetuhub.in` TXT record
- **Support Email:** support@dhansetuhub.in

---

## Rollback Trigger Conditions

- SSL certificate invalid or expired
- DNS resolution failure
- API 5xx errors
- Database connectivity issues
- OAuth redirects broken
- Razorpay webhooks not working
- Email delivery failures
- Error rate > 5%

**Rollback Time:** 10-15 minutes (restore from backup, revert config, restart services)

---

## Post-Launch SLAs

- **Uptime:** 99.9% (monthly)
- **Response Time:** < 200ms (p95)
- **Error Rate:** < 0.1%
- **SSL Certificate:** Valid, 30+ days validity
- **DNS Propagation:** < 5 minutes (reduced TTL)

---

## Quick Troubleshooting

### DNS Not Resolving
```bash
# Check propagation
dig dhansetuhub.in @8.8.8.8 +short A
dig dhansetuhub.in @ns1.cloudflare.com +short A

# Verify nameservers at registrar
dig NS dhansetuhub.in +short
```

### SSL Certificate Error
```bash
# Check certificate
echo | openssl s_client -connect dhansetuhub.in:443 -showcerts

# Verify Cloudflare setting
# Dashboard > SSL/TLS > Should show "Full"
```

### API Returns 404/500
```bash
# Check service status
systemctl status dhansetuhub-api

# Check logs
tail -100 /var/log/dhansetuhub-api.log | grep ERROR

# Verify environment
env | grep -i DOMAIN
```

### OAuth Redirect Loop
```bash
# Clear cookies, try incognito
# Verify Google Cloud Console has correct redirect URI

# Restart API
systemctl restart dhansetuhub-api
```

### Email Not Sending
```bash
# Test SMTP
python -c "import smtplib; smtp = smtplib.SMTP('smtp.gmail.com', 587); smtp.starttls(); print('OK')"

# Check SPF/DMARC
dig dhansetuhub.in TXT +short | grep -i spf
```

---

## Success Criteria

All of these must be true for successful launch:

- [ ] DNS resolves to dhansetuhub.in
- [ ] SSL certificate is valid
- [ ] HTTPS redirects from HTTP
- [ ] API responds with 200
- [ ] OAuth redirects work
- [ ] Razorpay webhooks respond
- [ ] Email sends successfully
- [ ] Database connectivity verified
- [ ] No critical errors in logs
- [ ] Error rate < 0.1%

---

## Support & Escalation

**Pre-Cutover Questions:**
- Refer to: `/Users/apple/shakthi-os/DOMAIN_CUTOVER_GUIDE.md`

**Infrastructure Questions:**
- Refer to: `/Users/apple/shakthi-os/DOMAIN_INFRASTRUCTURE_SUMMARY.md`

**Technical Implementation:**
- Refer to: `/Users/apple/shakthi-os/orchestrator/domain_*.py`

**During Cutover:**
- Slack: #dhansetuhub-domain-cutover
- On-call: [Engineering Lead Name]
- Escalation: [VP Engineering Name]

---

## Execution Checklist

### Before Cutover (24-48 hours prior)
- [ ] Read DOMAIN_CUTOVER_GUIDE.md completely
- [ ] Run `verify_domain_infrastructure.sh`
- [ ] Create database backups (2+ copies)
- [ ] Verify all DNS records in Cloudflare
- [ ] Update OAuth URIs in Google Console
- [ ] Update Razorpay webhook URLs
- [ ] Brief support team and on-call engineer
- [ ] Reduce TTL to 300 seconds

### During Cutover
- [ ] Deploy application code
- [ ] Update nameservers at registrar (if not already done)
- [ ] Monitor DNS propagation
- [ ] Run 10-point validation checklist
- [ ] Notify team of completion
- [ ] Begin continuous monitoring

### After Cutover (0-24 hours)
- [ ] Monitor error logs every 5 minutes (0-4h)
- [ ] Generate hourly health reports
- [ ] Check payment processing
- [ ] Verify email delivery
- [ ] Confirm OAuth flows work
- [ ] Document any issues
- [ ] Celebrate successful launch! 🎉

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-10-01 | Initial infrastructure deployment |

---

**Ready for Phase 3 Launch!** 🚀

For detailed procedures, see [DOMAIN_CUTOVER_GUIDE.md](./DOMAIN_CUTOVER_GUIDE.md)
