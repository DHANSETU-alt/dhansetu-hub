# Domain Cutover Guide: dhansetuhub.in Deployment

**Status:** Ready for Phase 3 Launch  
**Target Domain:** dhansetuhub.in  
**Current Temporary Domain:** dhansetuhub.workers.dev  
**Cutover Window:** Scheduled coordination required  
**Estimated Duration:** 2-4 hours (DNS propagation: 24-48 hours)

---

## Table of Contents
1. [Pre-Cutover Checklist](#pre-cutover-checklist)
2. [DNS Configuration](#dns-configuration)
3. [Pre-Cutover Preparation (24 Hours Before)](#pre-cutover-preparation)
4. [Cutover Procedure (Atomic Switching)](#cutover-procedure-atomic-switching)
5. [Post-Cutover Validation](#post-cutover-validation)
6. [Rollback Procedure](#rollback-procedure)
7. [Post-Launch Monitoring](#post-launch-monitoring)
8. [Troubleshooting](#troubleshooting)

---

## Pre-Cutover Checklist

### Infrastructure & Hosting
- [ ] Cloudflare account created and verified
- [ ] dhansetuhub.in domain added to Cloudflare
- [ ] Cloudflare nameservers noted
- [ ] SSL certificate provisioned (Cloudflare's automatic Let's Encrypt)
- [ ] Workers.dev backup verified (rollback target)
- [ ] Database backups created (at least 2 copies, different locations)
- [ ] Database integrity checks passing

### Configuration & Secrets
- [ ] Environment variables prepared (.env file)
- [ ] API keys secured in environment (not in code)
- [ ] Cloudflare API token configured
- [ ] Razorpay webhook URLs prepared for migration
- [ ] Google OAuth redirect URIs updated (approved in Google Console)
- [ ] SMTP credentials verified (email sending test passed)

### Application Testing
- [ ] SSL certificate chain verified
- [ ] All API endpoints tested on workers.dev
- [ ] Payment flow tested with Razorpay sandbox
- [ ] OAuth (Google Sign-In) flow tested
- [ ] Email notifications tested
- [ ] CSV import/export tested
- [ ] Database queries tested at scale
- [ ] Caching layer verified

### Security Verification
- [ ] Security headers configured (CSP, X-Frame-Options, etc.)
- [ ] CORS headers verified
- [ ] Rate limiting configured
- [ ] DDoS protection enabled on Cloudflare
- [ ] No hardcoded secrets in code or configs
- [ ] Dependency vulnerability scan passed
- [ ] Security audit completed

### Data Integrity
- [ ] Database schema matches both source and target
- [ ] User data backup completed
- [ ] Razorpay transaction history exported
- [ ] Research content/articles backup completed
- [ ] Referential integrity verified
- [ ] No orphaned records detected

### Team Readiness
- [ ] On-call engineer assigned
- [ ] Communication channels established (Slack, email)
- [ ] Rollback decision authority identified
- [ ] Customer support briefed
- [ ] Status page prepared (if applicable)
- [ ] Post-cutover monitoring enabled

---

## DNS Configuration

### 1. Cloudflare Zone Setup

**Action:** Add dhansetuhub.in to Cloudflare

```bash
# Verify domain ownership
# 1. Go to https://dash.cloudflare.com/
# 2. Add site: dhansetuhub.in
# 3. Select "Free" plan
# 4. Note the nameservers assigned:
#    - ns1.cloudflare.com
#    - ns2.cloudflare.com
#    (or similar ns*.cloudflare.com)
```

### 2. Update Registrar Nameservers

**Before Cutover (24-48 hours in advance):**

Go to your domain registrar (likely GoDaddy, Namecheap, etc.) and update nameservers to:
- `ns1.cloudflare.com`
- `ns2.cloudflare.com`

**Verification:**
```bash
dig NS dhansetuhub.in +short
# Should return Cloudflare nameservers
```

### 3. DNS Records Configuration

**In Cloudflare Dashboard:**

1. **A Record (Root Domain)**
   - Name: `@` (root)
   - Type: A
   - Content: Will be set to Cloudflare's IP once nameservers are active
   - TTL: 3600 (will reduce to 300 before cutover)
   - Proxy: Orange cloud (Cloudflare proxy)

2. **AAAA Record (IPv6)**
   - Name: `@`
   - Type: AAAA
   - Content: Cloudflare's IPv6 (auto-populated)
   - TTL: 3600 → 300 before cutover
   - Proxy: Orange cloud

3. **CNAME Record (www subdomain, optional)**
   - Name: `www`
   - Type: CNAME
   - Content: `dhansetuhub.in`
   - TTL: 3600 → 300 before cutover
   - Proxy: Orange cloud

4. **MX Records (Email)**
   - Priority 10: `aspmx.l.google.com`
   - Priority 20: `alt1.aspmx.l.google.com`
   - Priority 30: `alt2.aspmx.l.google.com`
   - Priority 40: `alt3.aspmx.l.google.com`
   - Priority 50: `alt4.aspmx.l.google.com`
   - TTL: 3600 → 300 before cutover

5. **TXT Records (SPF, DMARC)**
   - SPF: `v=spf1 include:_spf.google.com ~all`
   - DMARC: `v=DMARC1; p=quarantine; rua=mailto:dmarc@dhansetuhub.in`
   - TTL: 3600 → 300 before cutover

**Verification:**
```bash
# Check all records are configured
dig dhansetuhub.in +short A
dig dhansetuhub.in +short MX
dig dhansetuhub.in +short TXT
```

---

## Pre-Cutover Preparation (24 Hours Before)

### 1. TTL Reduction (Critical)

**Time: T-24 hours**

In Cloudflare, reduce TTL for all DNS records from 3600 to 300 seconds:
- This allows faster failover if issues occur
- Ensures clients pick up changes quickly

**Records to update:**
- A record (root domain)
- AAAA record
- CNAME record (www)
- MX records
- TXT records (SPF, DMARC)

### 2. Database Backup & Verification

**Time: T-12 hours**

```bash
# Full database backup
sqlite3 shakthi.db ".backup 'shakthi_backup_$(date +%Y%m%d_%H%M%S).db'"

# Verify backup integrity
sqlite3 shakthi_backup_*.db "PRAGMA integrity_check;"

# Export to off-system storage
# Option 1: Google Drive
gsutil cp shakthi_backup_*.db gs://backups/dhansetuhub/

# Option 2: External SSD
cp shakthi_backup_*.db /Volumes/External_Drive/Backups/

# List existing backups
ls -lh shakthi_backup_*.db
```

### 3. API Configuration Update (Stage)

**Time: T-12 hours (Staging Only - Do NOT deploy to production yet)**

Create new `.env` for dhansetuhub.in (keep workers.dev version as fallback):

```bash
# .env.dhansetuhub-staging
DOMAIN=dhansetuhub.in
API_URL=https://dhansetuhub.in
WORKERS_DOMAIN=dhansetuhub.workers.dev  # Keep for rollback
GOOGLE_OAUTH_REDIRECT_URI=https://dhansetuhub.in/api/auth/google/callback
RAZORPAY_WEBHOOK_URL=https://dhansetuhub.in/api/blackboxops/razorpay-webhook
```

### 4. OAuth & Integrations Pre-Configuration

**Time: T-12 hours**

**Google OAuth:**
1. Go to Google Cloud Console
2. Add to authorized redirect URIs:
   - `https://dhansetuhub.in/api/auth/google/callback`
3. Keep `https://dhansetuhub.workers.dev/api/auth/google/callback` (for rollback)

**Razorpay:**
1. Go to Razorpay Dashboard
2. Add webhook endpoint:
   - URL: `https://dhansetuhub.in/api/blackboxops/razorpay-webhook`
   - Events: payment.authorized, payment.failed, refund.created
3. Keep old endpoint active (for rollback)
4. Note webhook secret for new endpoint

**Email Configuration:**
1. Verify SPF and DMARC records in Cloudflare
2. Test email sending from `support@dhansetuhub.in`
3. Verify SMTP credentials work

### 5. Pre-Cutover Testing

**Time: T-6 hours**

```bash
# Run integration tests
python -m pytest tests/ -v --tb=short

# Test database connectivity
python orchestrator/db.py --health-check

# Test domain connectivity (once nameservers are updated)
curl -I https://dhansetuhub.in
dig dhansetuhub.in @ns1.cloudflare.com
dig dhansetuhub.in @8.8.8.8  # Check public DNS propagation

# Run domain monitoring
python orchestrator/domain_monitoring.py

# Check SSL certificate
echo | openssl s_client -connect dhansetuhub.in:443 -showcerts
```

### 6. Communication & Alerting

**Time: T-6 hours**

1. Notify team in Slack
2. Set up war room (Slack channel or Zoom link)
3. Prepare status page message (if applicable)
4. Brief customer support team

---

## Cutover Procedure (Atomic Switching)

### Phase 1: Final Checks (T-1 hour)

```bash
# 1. Verify no one is deploying code
git status
git log --oneline -5

# 2. Check current load/traffic
# (Check monitoring dashboard or request from DevOps)

# 3. Final database backup
sqlite3 shakthi.db ".backup 'shakthi_backup_final_$(date +%Y%m%d_%H%M%S).db'"

# 4. Verify DNS records are correctly set in Cloudflare
echo "=== Pre-cutover DNS Verification ==="
dig dhansetuhub.in @ns1.cloudflare.com +short A
dig dhansetuhub.in @ns1.cloudflare.com +short MX
```

### Phase 2: Application Deployment (T-0)

**CRITICAL: Execute these steps in order, without interruption**

```bash
# 1. Deploy new configuration to production
# (This should happen AFTER nameserver update but BEFORE or AT cutover time)
export DOMAIN=dhansetuhub.in
export API_URL=https://dhansetuhub.in
export WORKERS_DOMAIN=dhansetuhub.workers.dev  # Keep as fallback

# Apply new configuration
python orchestrator/startup.py --configure-domain dhansetuhub.in

# 2. Update application secrets/environment
# (Assuming secrets are loaded from environment, not code)
# No code change needed if using environment variables

# 3. Restart/redeploy application service
# If using Cloudflare Workers:
wrangler publish --env production

# If using traditional server:
systemctl restart dhansetuhub-api
systemctl restart dhansetuhub-web
```

### Phase 3: DNS Cutover (T+0)

**This is the actual switching point - coordinate with team**

```bash
# At this point, DNS should already be pointing to Cloudflare
# If NOT already changed at registrar, do it NOW:
# 1. Log into registrar (GoDaddy, Namecheap, etc.)
# 2. Update nameservers to Cloudflare's:
#    - ns1.cloudflare.com
#    - ns2.cloudflare.com

# Verify nameserver change
dig NS dhansetuhub.in +short
# Should show Cloudflare nameservers

# Monitor DNS propagation
watch -n 5 'dig dhansetuhub.in @8.8.8.8 +short A'
# Stop when it shows Cloudflare IPs consistently
```

### Phase 4: Verification (T+5 mins)

```bash
# 1. Test domain resolution
nslookup dhansetuhub.in
dig dhansetuhub.in +short A
dig dhansetuhub.in +short AAAA

# 2. Test HTTPS connectivity
curl -v https://dhansetuhub.in 2>&1 | grep -E "SSL|HTTP|Date"

# 3. Test SSL certificate
echo | openssl s_client -connect dhansetuhub.in:443 -showcerts 2>/dev/null | grep -E "subject=|issuer="

# 4. Test API endpoints
curl -X GET https://dhansetuhub.in/health -v
curl -X POST https://dhansetuhub.in/api/test -H "Content-Type: application/json" -d '{}' -v

# 5. Test OAuth redirect
# Visit https://dhansetuhub.in/login in browser
# Should redirect to Google OAuth with correct client ID

# 6. Monitor logs
tail -f /var/log/dhansetuhub-api.log
tail -f /var/log/dhansetuhub-web.log
```

---

## Post-Cutover Validation

### 10-Point Validation Checklist

**Complete each check within 15 minutes of cutover:**

- [ ] **DNS Resolution**: `dig dhansetuhub.in` returns Cloudflare IPs
- [ ] **SSL Certificate**: Certificate is valid and not self-signed
  ```bash
  openssl s_client -connect dhansetuhub.in:443 </dev/null 2>/dev/null | grep -E "CN=|subject="
  ```
- [ ] **HTTPS Redirect**: HTTP requests redirect to HTTPS
  ```bash
  curl -I http://dhansetuhub.in 2>&1 | grep -i location
  ```
- [ ] **API Health**: Health endpoint responds with 200
  ```bash
  curl -I https://dhansetuhub.in/health
  ```
- [ ] **OAuth Redirect**: Google OAuth URIs point to new domain
  ```bash
  curl -s https://dhansetuhub.in/api/auth/google | grep -i redirect
  ```
- [ ] **Razorpay Webhook**: Webhook endpoint accessible
  ```bash
  curl -X OPTIONS https://dhansetuhub.in/api/blackboxops/razorpay-webhook -v
  ```
- [ ] **Email Configuration**: Test email from support@dhansetuhub.in
  ```bash
  python -c "
  from orchestrator.email_gateway import send_test_email
  send_test_email('test@example.com')
  "
  ```
- [ ] **Database Connectivity**: Can read/write to production database
  ```bash
  python -c "
  from orchestrator.db import get_db
  db = get_db()
  print('DB Connected')
  "
  ```
- [ ] **Error Rates**: Application logs show no critical errors
  ```bash
  grep -i "ERROR\|CRITICAL" /var/log/dhansetuhub-api.log | tail -20
  ```
- [ ] **User Traffic**: Users can access site without errors
  - Visit https://dhansetuhub.in in browser
  - Navigate through main features
  - No console errors (open DevTools)

### Full Validation Report

```bash
#!/bin/bash
# Run this script to generate validation report

echo "=== dhansetuhub.in Cutover Validation Report ===" > validation_report.txt
echo "Generated: $(date -u)" >> validation_report.txt
echo "" >> validation_report.txt

echo "[1/10] DNS Resolution" >> validation_report.txt
dig dhansetuhub.in +short A >> validation_report.txt 2>&1
echo "" >> validation_report.txt

echo "[2/10] SSL Certificate" >> validation_report.txt
echo | openssl s_client -connect dhansetuhub.in:443 -showcerts 2>/dev/null | grep -E "subject=|issuer=" >> validation_report.txt 2>&1
echo "" >> validation_report.txt

echo "[3/10] HTTPS Redirect" >> validation_report.txt
curl -I http://dhansetuhub.in 2>&1 | head -5 >> validation_report.txt
echo "" >> validation_report.txt

echo "[4/10] API Health" >> validation_report.txt
curl -s https://dhansetuhub.in/health | jq . >> validation_report.txt 2>&1
echo "" >> validation_report.txt

echo "[5/10] OAuth Configuration" >> validation_report.txt
curl -s https://dhansetuhub.in/api/auth/google/config >> validation_report.txt 2>&1
echo "" >> validation_report.txt

echo "[6/10] Razorpay Webhook" >> validation_report.txt
curl -X OPTIONS -v https://dhansetuhub.in/api/blackboxops/razorpay-webhook >> validation_report.txt 2>&1
echo "" >> validation_report.txt

echo "[7/10] Database Status" >> validation_report.txt
python -c "from orchestrator.db import get_db; print('OK')" >> validation_report.txt 2>&1
echo "" >> validation_report.txt

echo "[8/10] Recent Errors" >> validation_report.txt
grep -i "ERROR" /var/log/dhansetuhub-api.log | tail -5 >> validation_report.txt 2>&1
echo "" >> validation_report.txt

echo "[9/10] Response Time" >> validation_report.txt
time curl -s https://dhansetuhub.in -o /dev/null >> validation_report.txt 2>&1
echo "" >> validation_report.txt

echo "[10/10] Domain Monitoring" >> validation_report.txt
python orchestrator/domain_monitoring.py >> validation_report.txt 2>&1

echo ""
echo "Validation report saved to validation_report.txt"
cat validation_report.txt
```

---

## Rollback Procedure

**Trigger rollback if ANY of these occur:**
- [ ] SSL certificate errors (invalid, expired, wrong domain)
- [ ] DNS resolution failures
- [ ] API endpoints returning 5xx errors
- [ ] Database connectivity failures
- [ ] OAuth redirects broken
- [ ] Razorpay webhooks not working
- [ ] Email sending failures
- [ ] Error rate > 5% above baseline

### Rollback Steps (Immediate)

```bash
#!/bin/bash
# Execute rollback - reverts to workers.dev

echo "INITIATING ROLLBACK to dhansetuhub.workers.dev"

# 1. Stop current service
systemctl stop dhansetuhub-api
systemctl stop dhansetuhub-web

# 2. Revert configuration to workers.dev
export API_URL=https://dhansetuhub.workers.dev
export DOMAIN=dhansetuhub.workers.dev

# 3. Restore from database backup
# (Use most recent backup from pre-cutover)
DB_BACKUP=$(ls -1 shakthi_backup_*.db | tail -1)
echo "Restoring from backup: $DB_BACKUP"
cp "$DB_BACKUP" shakthi.db

# 4. Restart services
systemctl start dhansetuhub-web
systemctl start dhansetuhub-api

# 5. Revert DNS (optional, depends on TTL propagation)
# In Cloudflare: Point A record back to workers.dev
# OR let workers.dev redirect to new domain if desired

# 6. Verify rollback
curl -I https://dhansetuhub.workers.dev/health
echo "Rollback complete. Investigating root cause..."

# 7. Notify team
# Message to #incidents channel:
# ⚠️ ROLLBACK: dhansetuhub.in cutover rolled back to workers.dev
# Reason: [describe issue]
# Time rolled back: [timestamp]
# Next steps: Investigation in #incidents channel
```

### Post-Rollback Analysis

1. **Investigate Root Cause**
   - Check application logs for errors
   - Review DNS propagation status
   - Check SSL certificate status
   - Verify database integrity

2. **Document Incident**
   - Create incident report
   - Note timeline of events
   - Record resolution steps

3. **Schedule Retry**
   - Fix identified issues
   - Repeat pre-cutover checklist
   - Schedule new cutover window

---

## Post-Launch Monitoring

### Immediate Monitoring (0-4 hours post-cutover)

```bash
# Watch these metrics continuously
watch -n 5 '
echo "=== DNS Status ==="; dig dhansetuhub.in @8.8.8.8 +short A
echo "=== HTTP Status ==="; curl -s -w "%{http_code}\n" -o /dev/null https://dhansetuhub.in
echo "=== Error Log ==="; tail -5 /var/log/dhansetuhub-api.log
'

# Monitor error rates in application
tail -f /var/log/dhansetuhub-api.log | grep -i ERROR

# Check Cloudflare dashboard for DDoS alerts, cache stats
# https://dash.cloudflare.com
```

### Extended Monitoring (4-24 hours post-cutover)

- [ ] SSL certificate expiry tracked (alert at 30 days)
- [ ] DNS resolution latency < 100ms
- [ ] API response time < 200ms (p95)
- [ ] Error rate < 0.1%
- [ ] No database connection timeouts
- [ ] Email delivery success rate > 99%
- [ ] OAuth flow success rate > 99.5%
- [ ] Razorpay webhook processing lag < 5 seconds

### Metrics & Alerts

Deploy monitoring configuration:

```bash
python orchestrator/domain_monitoring.py
# Generates monitoring_alerts.yaml for Datadog/New Relic integration

# Import alerts into your monitoring system:
# Datadog: datadog import monitoring_alerts.yaml
# New Relic: newrelic alerts import monitoring_alerts.yaml
```

---

## Troubleshooting

### Issue: DNS Not Resolving

**Symptoms:** `dig dhansetuhub.in` returns SERVFAIL or no answer

**Solution:**
```bash
# 1. Verify Cloudflare nameservers
dig NS dhansetuhub.in +short
# Should show ns1.cloudflare.com, ns2.cloudflare.com

# 2. Check propagation at different DNS servers
dig dhansetuhub.in @8.8.8.8 +short A      # Google DNS
dig dhansetuhub.in @1.1.1.1 +short A      # Cloudflare's DNS
dig dhansetuhub.in @ns1.cloudflare.com +short A

# 3. If not propagated, wait 15-30 minutes and retry
# (TTL has been reduced to 300s, but registrar changes take time)

# 4. Verify A record exists in Cloudflare
# Go to Cloudflare Dashboard > DNS > A record should show Cloudflare IP
```

### Issue: SSL Certificate Error

**Symptoms:** `curl https://dhansetuhub.in` shows certificate error

**Solution:**
```bash
# 1. Check certificate validity
echo | openssl s_client -connect dhansetuhub.in:443 -showcerts 2>/dev/null | grep -A 5 "subject="

# 2. Verify Cloudflare SSL setting
# Dashboard > SSL/TLS > Overview should show "Full"

# 3. If using "Full (strict)", ensure origin certificate is valid
# Can use Cloudflare's automatic certificate

# 4. Clear browser cache and retry
# Or use: curl -k https://dhansetuhub.in (insecure, for testing only)
```

### Issue: API Returns 404 or 500 Errors

**Symptoms:** `curl https://dhansetuhub.in/api/health` returns error

**Solution:**
```bash
# 1. Check if API service is running
systemctl status dhansetuhub-api
ps aux | grep dhansetuhub

# 2. Check logs for errors
tail -100 /var/log/dhansetuhub-api.log | grep -i error

# 3. Verify environment variables
env | grep -i DOMAIN
env | grep -i API_URL

# 4. Check database connectivity
python -c "from orchestrator.db import get_db; db = get_db(); print(db.execute('SELECT 1').fetchone())"

# 5. Restart API service
systemctl restart dhansetuhub-api
sleep 5
curl https://dhansetuhub.in/api/health
```

### Issue: OAuth Redirect Loop

**Symptoms:** Clicking "Sign in with Google" causes redirect loop

**Solution:**
```bash
# 1. Verify Google OAuth settings in Google Cloud Console
# Should include: https://dhansetuhub.in/api/auth/google/callback

# 2. Check application environment variable
echo $GOOGLE_OAUTH_REDIRECT_URI
# Should be: https://dhansetuhub.in/api/auth/google/callback

# 3. Restart API after changing env vars
systemctl restart dhansetuhub-api

# 4. Clear browser cookies and cache
# Open in new incognito window

# 5. Check logs for OAuth errors
grep -i "oauth\|redirect" /var/log/dhansetuhub-api.log
```

### Issue: Email Not Sending

**Symptoms:** Welcome emails or notifications not received

**Solution:**
```bash
# 1. Verify email configuration
env | grep -i SMTP

# 2. Test SMTP connectivity
python -c "
import smtplib
smtp = smtplib.SMTP('smtp.gmail.com', 587)
smtp.starttls()
print('SMTP OK')
"

# 3. Send test email
python -c "
from orchestrator.email_gateway import send_test_email
send_test_email('test@example.com')
print('Test email sent')
"

# 4. Check SPF/DMARC records
dig dhansetuhub.in TXT +short | grep -i spf
dig _dmarc.dhansetuhub.in TXT +short

# 5. Check email logs
tail -50 /var/log/dhansetuhub-api.log | grep -i mail
```

### Issue: Razorpay Webhooks Not Processing

**Symptoms:** Payments processed but orders not updated in system

**Solution:**
```bash
# 1. Verify webhook URL in Razorpay Dashboard
# Settings > Webhooks > https://dhansetuhub.in/api/blackboxops/razorpay-webhook

# 2. Test webhook endpoint
curl -X POST https://dhansetuhub.in/api/blackboxops/razorpay-webhook \
  -H "Content-Type: application/json" \
  -H "X-Razorpay-Signature: test" \
  -d '{"event":"payment.authorized"}'
# Should return 200 or 401/403 (not 404 or 500)

# 3. Check webhook logs
grep -i "razorpay\|webhook" /var/log/dhansetuhub-api.log

# 4. Verify webhook secret in environment
echo $RAZORPAY_WEBHOOK_SECRET

# 5. Restart API
systemctl restart dhansetuhub-api
```

---

## Communication Template

### Pre-Cutover Announcement

```
📢 Attention: dhansetuhub.in Domain Launch Scheduled

Tomorrow at [TIME] UTC, we'll be launching DhanSetu Hub on our new domain: dhansetuhub.in

🔄 What's Changing?
- New domain: dhansetuhub.in (replacing temporary dhansetuhub.workers.dev)
- Same functionality and data
- Improved performance via Cloudflare CDN
- Enhanced security with full SSL/TLS encryption

✓ What Won't Change
- User accounts and data (fully preserved)
- Payment history and transactions
- Research insights and articles
- Pricing and features

⏱️ Timeline
- Estimated cutover: [TIME] UTC (duration: 2-4 hours)
- Full DNS propagation: 24-48 hours
- Services may be unavailable during switching window

⚠️ What to Do
- Bookmark new domain: dhansetuhub.in
- Update bookmarks after cutover
- Clear browser cache if experiencing issues
- Contact support@dhansetuhub.in with questions

🚀 We're excited about this upgrade! Thank you for your patience.
```

### Post-Cutover Announcement

```
✅ Domain Cutover Complete!

dhansetuhub.in is now live! Your new domain is dhansetuhub.in

🎉 What You'll Notice
- Faster load times (Cloudflare global CDN)
- Better security (enterprise-grade SSL/TLS)
- Enhanced reliability (99.9% uptime SLA)
- Same great features and data

📍 New URLs
- Dashboard: https://dhansetuhub.in
- API: https://dhansetuhub.in/api
- Support: support@dhansetuhub.in

🔄 Migration Notes
- Your account data is fully preserved
- All payment history intact
- Research content migrated
- OAuth logins working with new domain

❓ Issues?
- Clear browser cache (Ctrl+Shift+Del)
- Try incognito mode
- Contact support@dhansetuhub.in

Thank you for being part of DhanSetu Hub!
```

---

## Sign-Off & Final Verification

**Pre-Cutover Sign-Off:**

- [ ] Infrastructure lead: _____________________ Date: _______
- [ ] Security lead: _________________________ Date: _______
- [ ] Product lead: __________________________ Date: _______
- [ ] On-call engineer: ______________________ Date: _______

**Post-Cutover Verification:**

- [ ] Cutover completed: _____________________ Date/Time: _______
- [ ] All validation checks passed: ___________ Verified by: _______
- [ ] Monitoring alerts active: ______________ Verified by: _______
- [ ] Team notified: ________________________ Date/Time: _______

---

**Document Control**
- Version: 1.0
- Last Updated: 2026-10-01
- Next Review: After successful cutover
- Approved by: Engineering Lead
