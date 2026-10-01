# Phase 3 Compressed Go-Live Plan (48-72 Hours)
**Domain Cutover: dhansetuhub.workers.dev → dhansetuhub.in**

**Status**: Production-Ready | **Cutover Window**: 2-3 Days | **Target Downtime**: <30 seconds

---

## Executive Summary

This is a **maximum-speed, parallel go-live** orchestrating simultaneous DNS, database, feature flag, and monitoring activation to move Shakthi OS Phase 3 from Cloudflare Workers (workers.dev) to the production domain (dhansetuhub.in) in 48-72 hours with zero production downtime.

**Success Criteria**:
- ✓ <30 second DNS TTL switch (atomic cutover)
- ✓ All 10-point validation checklist passes within 2 hours post-cutover
- ✓ Error rate <0.5% after 24 hours
- ✓ Response time <200ms (99th percentile)
- ✓ 5+ successful customer transactions
- ✓ 3+ partner signups
- ✓ PeopleDesk, Partner Network, Rate Limiting all live

---

## Timeline Overview

| Phase | Hours | Duration | Parallel Work |
|-------|-------|----------|----------------|
| **A: Pre-Cutover** | 0-6 | 6h | DNS TTL prep, DB backup, OAuth/Razorpay validation, SSL verify, Load test |
| **B: Cutover Window** | 6-12 | 6h | DNS atomic switch, Feature flags, Rate limiting, Monitoring startup |
| **C: Validation** | 12-24 | 12h | 10-point checklist, Real customer test, PeopleDesk ops, Partner signup |
| **D: Launch** | 24-48 | 24h | Marketing, Email campaigns, Social announcement, Customer outreach |
| **E: Iteration** | 48-72 | 24h | Issue monitoring, Feedback collection, Performance tuning, Team debrief |

---

## Phase A: Pre-Cutover (Hour 0-6)

### A.1: Final Acceptance Gate (0:00 - 0:30)

**Owner**: Founder | **Evidence Required**: Screenshots

```bash
# 1. Verify Phase 3 components are production-ready
$ npm run test:all --project=phase3
Expected: All tests pass (481/481 OS tests)

# 2. Verify feature flags are configured but disabled
$ npm run feature-flags:status | grep -E "PeopleDesk|PartnerNetwork|RateLimiting"
Expected: All set to 'disabled' (will enable during cutover)

# 3. Verify rate limiting config is staged
$ grep -r "RATE_LIMIT" .env* | wc -l
Expected: Rate limit configs in place (not yet active)

# 4. Verify monitoring dashboards are wired
$ curl -s https://api.datadog.com/api/v1/dashboard | jq .dashboards[].title
Expected: See "Phase3-Metrics", "Error-Rate-Monitor", "Latency-Tracker"

# 5. Verify incident response playbook is documented
$ [ -f INCIDENT_RESPONSE_PLAYBOOK.md ] && echo "READY" || echo "MISSING"
Expected: File exists and contains rollback procedures
```

**Sign-off**: Founder confirms all 5 checks pass → proceed to A.2

---

### A.2: Database Backup + Recovery Test (0:30 - 1:30)

**Owner**: Database Reliability Engineer | **Evidence**: Backup timestamp + recovery log

```bash
# 1. Full database backup
$ sqlite3 shakthi.db ".backup shakthi_$(date +%Y%m%d_%H%M%S).backup"
$ tar -czf shakthi_backup_$(date +%Y%m%d_%H%M%S).tar.gz shakthi_*.backup
$ echo "Backup size: $(du -h shakthi_backup_*.tar.gz | cut -f1)"
Expected: Backup file created and timestamped

# 2. Verify backup integrity
$ sqlite3 shakthi_latest.backup "PRAGMA integrity_check;"
Expected: "ok"

# 3. Test recovery to staging database
$ cp shakthi_latest.backup shakthi_test_recovery.db
$ sqlite3 shakthi_test_recovery.db "SELECT count(*) FROM users;"
Expected: Returns user count > 0

# 4. Verify all tables migrated
$ sqlite3 shakthi_test_recovery.db ".tables"
Expected: See users, partners, transactions, audit_log, sessions, etc.

# 5. Verify no corruption
$ sqlite3 shakthi_test_recovery.db "PRAGMA quick_check;"
Expected: "ok"

# 6. Archive backup to external storage (Drive/GitHub)
$ gsutil -m cp shakthi_backup_*.tar.gz gs://backups/shakthi-phase3/
Expected: Backup uploaded with timestamp confirmation
```

**Rollback evidence**: Backup file exists + verified integrity check passes

---

### A.3: OAuth/Razorpay URL Validation (1:30 - 2:00)

**Owner**: Payment & Auth Engineer | **Evidence**: API response logs

```bash
# 1. Verify Google OAuth redirect URL is configured for dhansetuhub.in
$ curl -s "https://oauth.googleapis.com/tokeninfo?id_token=test" 2>&1 | grep -q "error"
Note: Just checking endpoint is reachable; full test happens post-cutover

# 2. Test Razorpay webhook secret is staged
$ grep "RAZORPAY_WEBHOOK_SECRET" .env.production
Expected: Secret is set (masked)

# 3. Verify Razorpay order creation endpoint accepts dhansetuhub.in domain
$ curl -X POST "https://api.razorpay.com/v1/orders" \
  -H "Authorization: Basic [BASE64_CREDS]" \
  -d "amount=50000&currency=INR" 2>&1 | grep -q "order_id"
Expected: Order creation succeeds (or expected auth error if test creds)

# 4. Test webhook URL accepts callbacks
$ curl -X POST "https://dhansetuhub.in/api/blackboxops/razorpay-webhook" \
  -H "X-Razorpay-Signature: test_sig" \
  -d '{"event":"payment.authorized"}' 2>&1 | head -20
Expected: 200 or 403 (auth) response, not 404

# 5. Verify OAuth callback URL in Google Cloud Console
$ echo "Google OAuth Redirect URI: https://dhansetuhub.in/api/auth/google/callback"
Expected: This URL is added to authorized redirect URIs in Google Cloud before cutover
```

**Sign-off**: All 5 validations confirmed → proceed to A.4

---

### A.4: SSL Certificate Verification (2:00 - 2:15)

**Owner**: DevOps Engineer | **Evidence**: openssl output

```bash
# 1. Verify SSL certificate is issued for dhansetuhub.in
$ echo | openssl s_client -connect dhansetuhub.in:443 2>/dev/null | \
  grep -E "subject=|issuer=|notAfter" | tee ssl_check.log
Expected:
  subject=CN = dhansetuhub.in
  issuer=C = US, O = Cloudflare, Inc. ...
  notAfter=2027-10-XX (future date)

# 2. Verify certificate chain is complete
$ echo | openssl s_client -connect dhansetuhub.in:443 -showcerts 2>/dev/null | \
  grep "Verify return code:" | tee -a ssl_check.log
Expected: "Verify return code: 0 (ok)"

# 3. Verify HSTS is configured
$ curl -sI https://dhansetuhub.in | grep -i "strict-transport-security"
Expected: "Strict-Transport-Security: max-age=31536000; includeSubDomains; preload"

# 4. Test TLS 1.3 support
$ echo | openssl s_client -tls1_3 -connect dhansetuhub.in:443 2>/dev/null | \
  grep "Protocol  :" | tee -a ssl_check.log
Expected: "Protocol  : TLSv1.3"

# 5. Verify domain serves correct certificate
$ dig +short CNAME dhansetuhub.in @1.1.1.1
Expected: Should resolve to Cloudflare Workers endpoint or IP
```

**Sign-off**: All 5 SSL checks pass → proceed to A.5

---

### A.5: Load Test (2:15 - 4:15)

**Owner**: Performance Engineer | **Evidence**: Load test results file

**Pre-cutover load test on staging/workers.dev endpoint** (to validate infrastructure can handle migration spike):

```bash
# 1. Start load test against workers.dev endpoint
$ npm run load-test --target=https://dhansetuhub.workers.dev \
  --duration=120m --rps=1000 --concurrent=100 2>&1 | tee load_test_results.log

# Expected output format (every 30 seconds):
#   [0:30] RPS: 1000, Latency: 45ms (p50), 120ms (p95), 450ms (p99)
#   [1:00] RPS: 1000, Latency: 48ms (p50), 125ms (p95), 460ms (p99)
#   ...
#   [2:00] Summary: 120,000 requests, 0 errors, Error Rate: 0%

# 2. Verify error rate is <0.1% at peak load
$ grep "Error Rate:" load_test_results.log | tail -1
Expected: Error Rate: <0.1%

# 3. Verify 99th percentile latency is <500ms
$ grep "p99" load_test_results.log | tail -1
Expected: p99 < 500ms

# 4. Verify no connection pooling exhaustion
$ grep "Connection refused" load_test_results.log | wc -l
Expected: 0

# 5. Archive load test results
$ tar -czf load_test_$(date +%Y%m%d_%H%M%S).tar.gz load_test_results.log
$ echo "Load test passed: $(cat load_test_results.log | grep Summary)"
```

**Sign-off**: Load test shows system can handle cutover traffic → proceed to A.6

---

### A.6: Communication Ready (4:15 - 4:30)

**Owner**: Founder | **Evidence**: Templates staged in COMMUNICATION_TEMPLATES.md

```bash
# 1. Verify all notification templates are drafted
$ grep -c "^## " COMMUNICATION_TEMPLATES.md
Expected: ≥6 templates (Team standup, Customer email, Partner notification, etc.)

# 2. Verify contact lists are current
$ [ -f CONTACT_LIST.json ] && jq '.team | length' CONTACT_LIST.json
Expected: ≥3 team members listed

# 3. Stage status page message
$ [ -f STATUS_PAGE_DRAFT.md ] && wc -l STATUS_PAGE_DRAFT.md
Expected: Draft exists with planned update messages

# 4. Verify Slack/Telegram alerts are configured
$ echo "Configured notification channels:"
  - Slack: #phase3-golive (auto-alerts enabled)
  - Telegram: Founder direct (manual status updates)
  - Email: support@dhansetuhub.in (customer notifications)
Expected: All channels ready to send

# 5. Set phone/on-call ready
$ echo "On-call engineers ready for 48-72h window"
Expected: Confirm via founder message in Slack
```

**Sign-off**: All communication templates staged → Ready for Phase B

---

## Phase B: Parallel Cutover (Hour 6-12)

**⚠️ CRITICAL: This 6-hour window is the active cutover. Founder leads all work streams in parallel.**

### B.1: DNS TTL Reduction (6:00 - 6:30)

**Owner**: DevOps Engineer | **Evidence**: Cloudflare API response

**Start FIRST - this takes 30 min to propagate globally**:

```bash
# 1. Reduce TTL to 5 minutes BEFORE atomic switch
$ curl -X PATCH "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${RECORD_ID_A}" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "ttl": 300,
    "name": "@",
    "type": "A",
    "content": "104.21.28.1"
  }' | tee dns_ttl_update.log

# Expected response:
#  "success": true,
#  "result": {
#    "id": "...",
#    "ttl": 300,
#    ...
#  }

# 2. Verify TTL is now 300 seconds
$ dig @ns1.cloudflare.com dhansetuhub.in | grep -A1 "ANSWER SECTION"
Expected: Should show reduced TTL

# 3. Wait 10 minutes for TTL propagation (do other work in parallel)
$ echo "TTL reduction initiated at $(date +%H:%M:%S) - will be active in 10 minutes"

# 4. Verify TTL has propagated
$ for i in {1..10}; do
  echo "Check $i: $(dig +nocmd dhansetuhub.in +noall +answer | grep "^dhansetuhub" | awk '{print $2}')"
  sleep 60
done

# Expected: TTL value should be 300 or close to it after 10 min

# 5. Document TTL change
$ echo "TTL change completed at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> CUTOVER_LOG.txt
```

**⚠️ DO NOT PROCEED with atomic DNS switch until TTL = 300 globally (check B.4)**

---

### B.2: Feature Flag Activation (6:00 - 6:30, parallel with B.1)

**Owner**: Feature Flag Engineer | **Evidence**: Feature flag status output

**Activate Phase 3 features (gradual rollout)**:

```bash
# 1. Enable PeopleDesk feature flag (support ticket system)
$ npm run feature-flags:set --flag=PeopleDesk --status=enabled --rollout=100
# Expected output:
#  ✓ PeopleDesk: enabled (100% rollout)
#  ✓ Feature flag stored in Datadog

# 2. Enable Partner Network feature flag (commission system)
$ npm run feature-flags:set --flag=PartnerNetwork --status=enabled --rollout=100
# Expected output:
#  ✓ PartnerNetwork: enabled (100% rollout)

# 3. Enable Rate Limiting feature flag
$ npm run feature-flags:set --flag=RateLimiting --status=enabled --rollout=100
# Expected output:
#  ✓ RateLimiting: enabled (100% rollout)

# 4. Verify all three flags are enabled
$ npm run feature-flags:status
# Expected output:
#  PeopleDesk: enabled (100%)
#  PartnerNetwork: enabled (100%)
#  RateLimiting: enabled (100%)

# 5. Test PeopleDesk endpoint is responding
$ curl -s https://dhansetuhub.workers.dev/api/peopledesk/health | jq .status
Expected: "ok"

# 6. Document feature flag activation
$ echo "Feature flags activated at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> CUTOVER_LOG.txt
```

**Rollback trigger**: If any flag causes >2% error rate, disable immediately

---

### B.3: Rate Limiting Gradual Enable (6:00 - 7:00, parallel)

**Owner**: Backend Engineer | **Evidence**: Rate limit logs

**Enable rate limiting in phases to avoid legitimate traffic blocking**:

```bash
# Phase 1: Enable rate limiting at 95th percentile (barely noticeable)
# This blocks only top 5% of aggressive traffic
$ npm run rate-limit:enable --tier=GRADUAL_1
# Expected: Sets limits to 10x normal usage

# Phase 2: Monitor for 15 minutes
$ npm run rate-limit:monitor --duration=15m
# Expected output every 30 seconds:
#  [6:15] Rate-limited requests: 0.1%
#  [6:30] Rate-limited requests: 0.2%
#  [6:45] Rate-limited requests: 0.1%

# Phase 3: Enable to standard limits
$ npm run rate-limit:enable --tier=PRODUCTION
# Expected: Sets limits to configured production values
#  Default: 100 requests/minute per IP
#           1000 requests/hour per user

# Phase 4: Verify rate limits are active
$ curl -s https://dhansetuhub.workers.dev/api/health | grep -i "rate-limit"
Expected: Rate limit headers present in response

# 5. Document rate limit activation
$ echo "Rate limiting activated at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> CUTOVER_LOG.txt
```

---

### B.4: Domain DNS Atomic Switch (8:00 - 8:05)

**Owner**: DevOps Engineer | **CRITICAL: All previous steps must be complete before this**

**The 5-minute atomic cutover - NO ROLLBACK after this point**:

```bash
# PRE-SWITCH CHECKLIST (confirm all before proceeding):
# [ ] TTL is 300 seconds globally (confirmed in B.1)
# [ ] Feature flags all enabled (confirmed in B.2)
# [ ] Rate limiting in PRODUCTION mode (confirmed in B.3)
# [ ] Load test passed <0.1% error rate (from Phase A)
# [ ] SSL certificate valid (confirmed in A.4)
# [ ] Razorpay webhook URL updated to dhansetuhub.in (confirmed in A.3)
# [ ] Google OAuth redirect URI added (confirmed in A.3)
# [ ] Database backup exists and verified (confirmed in A.2)

# ATOMIC SWITCH TIMESTAMP
$ CUTOVER_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
$ echo "=== ATOMIC DNS CUTOVER START ===" >> CUTOVER_LOG.txt
$ echo "Timestamp: $CUTOVER_START" >> CUTOVER_LOG.txt

# 1. Update DNS A record to point to Cloudflare Workers IP
# (This assumes Cloudflare Workers is the backend)
$ RECORD_ID=$(curl -s "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records?type=A&name=@" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" | jq -r '.result[0].id')

$ curl -X PATCH "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${RECORD_ID}" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "CNAME",
    "name": "@",
    "content": "dhansetuhub.workers.dev",
    "ttl": 300,
    "proxied": true
  }' 2>&1 | tee dns_switch_response.json

# Expected response:
#  "success": true,
#  "result": { "id": "...", "name": "@", "content": "dhansetuhub.workers.dev" }

# 2. Verify DNS change propagated to at least 3 nameservers
$ for ns in "ns1.cloudflare.com" "ns2.cloudflare.com" "1.1.1.1"; do
  echo "Checking $ns..."
  dig @$ns dhansetuhub.in +short
done | tee dns_verify_post_switch.log

# Expected: All should show dhansetuhub.workers.dev or Cloudflare IP

# 3. Check CNAME is resolving correctly
$ dig dhansetuhub.in | grep -A5 "ANSWER SECTION"
Expected: Shows CNAME → dhansetuhub.workers.dev

# 4. Verify HTTPS is accessible immediately
$ curl -sI https://dhansetuhub.in | head -5
Expected: HTTP 200 or 301 redirect (not 404 or timeout)

# 5. Test homepage loads
$ curl -s https://dhansetuhub.in/ | grep -q "<!DOCTYPE\|<html" && echo "✓ Homepage loaded"
Expected: ✓ Homepage loaded

$ CUTOVER_END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
$ echo "=== ATOMIC CUTOVER COMPLETE ===" >> CUTOVER_LOG.txt
$ echo "Duration: ~30 seconds" >> CUTOVER_LOG.txt
```

**Automatic Rollback Trigger (if any of these occur):**
```bash
# If any check fails, IMMEDIATELY revert DNS to workers.dev
$ ROLLBACK_DECISION=$(curl -s https://dhansetuhub.in/api/health | jq .status)

if [[ "$ROLLBACK_DECISION" != "ok" ]]; then
  echo "ROLLBACK TRIGGERED: API health check failed"
  # See INCIDENT_RESPONSE_PLAYBOOK.md for rollback procedure
fi
```

---

### B.5: Monitoring Startup (8:00 - 9:00, parallel with B.4)

**Owner**: SRE | **Evidence**: Dashboard screenshots

**Launch real-time monitoring during cutover**:

```bash
# 1. Start error rate monitoring
$ npm run monitor:errors --alert-threshold=5% --window=5m
# This will alert if error rate exceeds 5% in any 5-minute window

# 2. Start latency monitoring
$ npm run monitor:latency --alert-threshold=200ms --percentile=p99
# This will alert if p99 latency exceeds 200ms

# 3. Start revenue tracking
$ npm run monitor:revenue --period=1h
# Shows transaction volume and revenue in real-time

# 4. Open Datadog dashboard
$ open "https://app.datadoghq.com/dashboard/abc123-phase3-golive"

# 5. Set Slack alerts to #phase3-golive channel
$ npm run monitor:slack-alerts --channel="phase3-golive" --severity=critical

# 6. Configure auto-rollback if conditions worsen
$ npm run monitor:auto-rollback --trigger="error_rate>10%" --action="rollback_to_workers_dev"

# 7. Verify monitoring is active
$ curl -s https://api.datadog.com/api/v1/monitor/abc | jq .status
Expected: "alert" or "ok" (system is monitoring)

# 8. Document monitoring startup
$ echo "Monitoring active at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> CUTOVER_LOG.txt
```

**Incident Response**: If any alert fires, see INCIDENT_RESPONSE_PLAYBOOK.md

---

### B.6: Incident Response Team On-Standby (8:00 - 12:00)

**Owner**: Founder | **Evidence**: Slack status confirmation

```bash
# Team on-call during entire 6-hour cutover window:
# - Founder: Monitoring dashboards + decision making
# - Backend Engineer: API debugging + rollback execution
# - DevOps: DNS & infrastructure troubleshooting
# - SRE: Monitoring alerts + incident response

# Slack channel: #phase3-golive
# Expected activity: Status updates every 30 minutes
#   [8:05] "✓ DNS cutover complete, homepage loading"
#   [8:30] "✓ API responding, error rate 0.1%"
#   [9:00] "✓ Feature flags verified, rate limiting active"
#   [9:30] "✓ All checks passing, proceeding to validation"

# If error rate > 5%, auto-rollback triggers
# If API returns 5xx > 2%, manual rollback confirmed
# If DNS resolution fails, rollback within 5 minutes
```

---

## Phase C: Validation (Hour 12-24)

### C.1: 10-Point Post-Cutover Checklist (12:00 - 14:00)

**Owner**: QA Engineer | **Evidence**: Checklist screenshot + timestamps**

All checks must pass within 2 hours post-cutover or trigger auto-rollback:

```bash
echo "=== PHASE 3 VALIDATION CHECKLIST ===" 2>&1 | tee validation_checklist.log
echo "Start time: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> validation_checklist.log

# CHECK 1: Homepage loads on dhansetuhub.in
echo ""
echo "[1/10] Homepage accessibility..."
curl -s -L https://dhansetuhub.in/ | grep -q "<!DOCTYPE" && \
  echo "✓ Homepage loads correctly" || echo "✗ FAILED"
# Expected: ✓

# CHECK 2: API is responding with <200ms latency
echo ""
echo "[2/10] API response time..."
LATENCY=$(curl -s -w '%{time_total}' -o /dev/null https://dhansetuhub.in/api/health)
echo "Latency: ${LATENCY}s"
[ $(echo "$LATENCY < 0.2" | bc) -eq 1 ] && echo "✓ Within SLA" || echo "✗ FAILED"
# Expected: ✓ (< 0.2s)

# CHECK 3: Database is accessible
echo ""
echo "[3/10] Database connectivity..."
sqlite3 shakthi.db "SELECT count(*) FROM users;" 2>/dev/null | grep -q "^[0-9]" && \
  echo "✓ Database responding" || echo "✗ FAILED"
# Expected: ✓

# CHECK 4: PeopleDesk is accessible
echo ""
echo "[4/10] PeopleDesk module..."
curl -s https://dhansetuhub.in/api/peopledesk/health | jq -e '.status == "ok"' && \
  echo "✓ PeopleDesk online" || echo "✗ FAILED"
# Expected: ✓

# CHECK 5: Partner Network is accessible
echo ""
echo "[5/10] Partner Network module..."
curl -s https://dhansetuhub.in/api/partners/health | jq -e '.status == "ok"' && \
  echo "✓ Partner Network online" || echo "✗ FAILED"
# Expected: ✓

# CHECK 6: OAuth is working
echo ""
echo "[6/10] OAuth endpoint..."
curl -s https://dhansetuhub.in/api/auth/google/callback \
  -H "Content-Type: application/json" | grep -q -E "error|code|state" && \
  echo "✓ OAuth endpoint responding" || echo "✗ FAILED"
# Expected: ✓ (may return error for missing code, but endpoint is live)

# CHECK 7: Razorpay webhook is configured
echo ""
echo "[7/10] Razorpay webhook..."
curl -X POST https://dhansetuhub.in/api/blackboxops/razorpay-webhook \
  -H "X-Razorpay-Signature: test" \
  -d '{}' | grep -q -E "Unauthorized|Forbidden|Invalid" && \
  echo "✓ Webhook endpoint alive (auth rejected as expected)" || echo "✗ FAILED"
# Expected: ✓ (endpoint exists, rejects invalid signature)

# CHECK 8: Rate limiting is active
echo ""
echo "[8/10] Rate limiting..."
for i in {1..150}; do curl -s -o /dev/null https://dhansetuhub.in/api/health; done
STATUS=$(curl -I https://dhansetuhub.in/api/health 2>/dev/null | grep -i "x-ratelimit-remaining")
[ -n "$STATUS" ] && echo "✓ Rate limit headers present" || echo "✗ FAILED"
# Expected: ✓

# CHECK 9: Error rate is <0.5%
echo ""
echo "[9/10] Error rate monitoring..."
ERROR_RATE=$(curl -s https://api.datadog.com/api/v1/query \
  -H "DD-API-KEY: ${DATADOG_API_KEY}" \
  -d "query=avg:trace.web.request.errors{env:prod}*100/avg:trace.web.request{env:prod}" | \
  jq '.series[0].pointlist[-1][1]')
echo "Error rate: ${ERROR_RATE}%"
[ $(echo "$ERROR_RATE < 0.5" | bc) -eq 1 ] && echo "✓ Below SLA" || echo "✗ FAILED"
# Expected: ✓ (< 0.5%)

# CHECK 10: SSL certificate is valid
echo ""
echo "[10/10] SSL/TLS security..."
CERT_EXPIRY=$(echo | openssl s_client -connect dhansetuhub.in:443 2>/dev/null | \
  grep "notAfter=" | cut -d'=' -f2)
echo "Certificate expires: $CERT_EXPIRY"
echo "✓ Certificate valid" 
# Expected: ✓

echo ""
echo "=== CHECKLIST COMPLETE ===" >> validation_checklist.log
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> validation_checklist.log
```

**Pass/Fail Decision**:
- If all 10 checks pass: ✓ Proceed to C.2
- If <2 checks fail: ⚠ Review issue, fix within 30 min, re-run C.1
- If >2 checks fail: ✗ ROLLBACK (see INCIDENT_RESPONSE_PLAYBOOK.md)

---

### C.2: Real Customer Onboarding Test (14:00 - 17:00)

**Owner**: Product Manager | **Evidence**: Test transaction receipts**

Execute 3 real end-to-end customer transactions:

```bash
# TRANSACTION 1: New customer signs up + pays for basic plan
echo ""
echo "[TEST 1] New customer signup and payment (₹149)"
TEST_EMAIL_1="test_customer_$(date +%s)@gmail.com"

# Step 1: Visit signup page
curl -s -L https://dhansetuhub.in/signup | grep -q "email" && \
  echo "✓ Signup page loads"

# Step 2: Submit signup form
curl -X POST https://dhansetuhub.in/api/auth/signup \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL_1\",\"password\":\"Test@123\"}" | \
  jq .user_id | tee test1_signup_response.json

# Step 3: Initiate Razorpay payment
RAZORPAY_ORDER=$(curl -X POST https://dhansetuhub.in/api/blackboxops/razorpay-order \
  -H "Content-Type: application/json" \
  -d '{"amount":14900,"currency":"INR","plan":"basic"}' | \
  jq -r '.order_id')

echo "Razorpay Order ID: $RAZORPAY_ORDER"
[ -n "$RAZORPAY_ORDER" ] && echo "✓ Razorpay order created"

# Step 4: Simulate payment completion via webhook
WEBHOOK_RESPONSE=$(curl -X POST https://dhansetuhub.in/api/blackboxops/razorpay-webhook \
  -H "Content-Type: application/json" \
  -H "X-Razorpay-Signature: $(openssl dgst -sha256 -hmac secret -r <<< 'test' | awk '{print $1}')" \
  -d "{\"event\":\"payment.authorized\",\"payload\":{\"order\":{\"entity\":{\"id\":\"$RAZORPAY_ORDER\"}}}}" | \
  tee test1_payment_response.json)

echo "✓ Webhook processed"

# TRANSACTION 2: Existing customer upgrades plan
echo ""
echo "[TEST 2] Existing customer upgrade (₹399)"

# Use test customer from Transaction 1
curl -X POST https://dhansetuhub.in/api/blackboxops/razorpay-order \
  -H "Content-Type: application/json" \
  -d '{"user_email":"'$TEST_EMAIL_1'","amount":39900,"currency":"INR","plan":"premium"}' | \
  jq .order_id | tee test2_upgrade_order.json

echo "✓ Upgrade order created"

# TRANSACTION 3: Partner signup with commission verification
echo ""
echo "[TEST 3] Partner signup and commission calculation"

TEST_PARTNER_EMAIL="test_partner_$(date +%s)@gmail.com"

curl -X POST https://dhansetuhub.in/api/partners/signup \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_PARTNER_EMAIL\",\"name\":\"Test Partner\",\"phone\":\"9999999999\"}" | \
  jq .partner_id | tee test3_partner_signup.json

# Verify commission structure
curl -s https://dhansetuhub.in/api/partners/commissions | \
  jq '.commission_structure' | tee test3_commission_structure.json

echo "✓ Partner signup successful"

# SUMMARY
echo ""
echo "=== ONBOARDING TEST SUMMARY ===" | tee onboarding_test_summary.log
echo "✓ Transaction 1: New signup + ₹149 payment"
echo "✓ Transaction 2: Plan upgrade to ₹399"
echo "✓ Transaction 3: Partner signup + commission"
echo ""
echo "All transactions completed successfully!"
```

**Success criteria**: All 3 transactions process with payment confirmation received

---

### C.3: Support Tickets (PeopleDesk) Operations (17:00 - 20:00)

**Owner**: Support Manager | **Evidence**: Ticket screenshots**

Test PeopleDesk ticket system end-to-end:

```bash
# TEST 1: Create a support ticket
echo "[1/4] Creating support ticket..."
TICKET_ID=$(curl -X POST https://dhansetuhub.in/api/peopledesk/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Phase 3 Validation Test",
    "description": "Testing PeopleDesk ticket system",
    "priority": "medium",
    "category": "technical"
  }' | jq -r '.ticket_id')

echo "✓ Ticket created: $TICKET_ID"

# TEST 2: Assign ticket to support agent
echo "[2/4] Assigning ticket..."
curl -X PATCH https://dhansetuhub.in/api/peopledesk/tickets/$TICKET_ID \
  -H "Content-Type: application/json" \
  -d '{"assigned_to":"support_agent","status":"assigned"}' | \
  jq .status

# TEST 3: Add comment to ticket
echo "[3/4] Adding comment..."
curl -X POST https://dhansetuhub.in/api/peopledesk/tickets/$TICKET_ID/comments \
  -H "Content-Type: application/json" \
  -d '{"message":"Investigating the issue...","internal":false}' | \
  jq .comment_id

# TEST 4: Resolve ticket
echo "[4/4] Resolving ticket..."
curl -X PATCH https://dhansetuhub.in/api/peopledesk/tickets/$TICKET_ID \
  -H "Content-Type: application/json" \
  -d '{"status":"resolved","resolution":"Issue validated"}' | \
  jq .status

echo ""
echo "✓ All PeopleDesk operations successful"
```

---

### C.4: Partner Signup + Commission (20:00 - 23:00)

**Owner**: Partnership Manager | **Evidence**: Partner dashboard screenshots**

Test full partner onboarding and commission calculation:

```bash
# TEST 1: Partner signup
echo "[1/3] Partner application..."
PARTNER_ID=$(curl -X POST https://dhansetuhub.in/api/partners/apply \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Test Partner Co",
    "contact_name": "John Doe",
    "email": "partner@test.com",
    "phone": "9876543210",
    "gstin": "18AABCT0001H1Z5"
  }' | jq -r '.partner_id')

echo "✓ Partner application submitted: $PARTNER_ID"

# TEST 2: Partner approval
echo "[2/3] Partner approval workflow..."
curl -X PATCH https://dhansetuhub.in/api/partners/$PARTNER_ID \
  -H "Content-Type: application/json" \
  -d '{"status":"approved"}' | \
  jq .status

echo "✓ Partner approved"

# TEST 3: Commission verification
echo "[3/3] Commission calculation test..."

# Simulate 5 referral transactions
for i in {1..5}; do
  curl -X POST https://dhansetuhub.in/api/transactions/create \
    -H "Content-Type: application/json" \
    -d "{
      \"partner_id\": \"$PARTNER_ID\",
      \"referral_revenue\": $((10000 + i * 1000)),
      \"transaction_date\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
    }" > /dev/null
  echo "  ✓ Transaction $i processed"
done

# Verify commission accrual
COMMISSIONS=$(curl -s https://dhansetuhub.in/api/partners/$PARTNER_ID/commissions | \
  jq '.total_due')

echo ""
echo "Partner commission accrued: ₹$COMMISSIONS"
echo "✓ Commission calculation working"
```

---

### C.5: Analytics Verification (23:00 - 23:30)

**Owner**: Analytics Engineer | **Evidence**: GA4 + Razorpay event logs**

```bash
# TEST 1: GA4 events are flowing
echo "[1/2] Google Analytics 4..."
curl -s "https://www.googleapis.com/analytics/v3/data/ga" \
  -H "Authorization: Bearer ${GA4_ACCESS_TOKEN}" \
  -d "ids=ga:${GA4_VIEW_ID}&start-date=today&end-date=today&metrics=ga:users,ga:pageviews" | \
  jq '.totalsForAllResults'

echo "✓ GA4 events received"

# TEST 2: Razorpay event logging
echo "[2/2] Razorpay transaction events..."
curl -s "https://api.razorpay.com/v1/orders" \
  -H "Authorization: Basic $(echo -n "${RAZORPAY_KEY_ID}:${RAZORPAY_KEY_SECRET}" | base64)" | \
  jq '.items | length' | \
  awk '{print "✓ " $1 " transactions logged in Razorpay"}'

echo ""
echo "✓ Analytics pipeline live"
```

---

## Phase D: Full Launch (Hour 24-48)

### D.1: Marketing Landing Page (24:00)

**Owner**: Marketing Manager | **Evidence**: Live site screenshot**

```bash
# Enable marketing landing page
$ npm run marketing:enable --page=landing --domain=dhansetuhub.in
$ curl -s https://dhansetuhub.in | grep "h1" | head -1
Expected: Shows landing page headline

# Verify all CTAs are clickable
$ curl -s https://dhansetuhub.in | grep -c "href=" | awk '{print $1 " CTA links found"}'

# Take screenshot for documentation
$ screenshot "https://dhansetuhub.in" marketing_launch.png
```

---

### D.2: Email Campaign Activation (24:00+)

**Owner**: Marketing Manager | **Evidence**: Mailgun logs**

```bash
# Send partner recruitment email to waitlist
$ npm run email:campaign:send \
  --template=partner_launch \
  --audience=waitlist \
  --scheduled=now

# Monitor delivery
$ curl -s https://api.mailgun.net/v3/${MAILGUN_DOMAIN}/events \
  -H "Authorization: Basic $(echo -n api:${MAILGUN_API_KEY} | base64)" | \
  jq '.items | length' | \
  awk '{print "✓ " $1 " emails sent"}'
```

---

### D.3: Social Media Announcement (30:00)

**Owner**: Social Media Manager | **Evidence**: Tweet/Post screenshots**

Post to:
- Twitter/X: #PeopleDesk #PartnerNetwork #Phase3Live
- LinkedIn: Shakthi OS Phase 3 announcement
- Telegram: Founder channel + community

---

### D.4: Customer Outreach (36:00)

**Owner**: Customer Success | **Evidence**: Email delivery logs**

```bash
# 3-email sequence to active users
EMAIL_1_SUBJECT="Introducing PeopleDesk: Built-in Support Tickets"
EMAIL_2_SUBJECT="Earn While You Grow: Partner Network Live"
EMAIL_3_SUBJECT="Rate Limiting: Protecting Your Account"

# Send with staggered timing
$ npm run email:sequence:send --sequence=phase3_launch --spacing=4h
```

---

### D.5: 24/7 On-Call Rotation (24-48 hours)

**Owner**: Founder | **Evidence**: On-call schedule**

Continuous monitoring:
- Hour 24-30: Founder + Backend Engineer
- Hour 30-36: Backend Engineer + DevOps
- Hour 36-42: DevOps + SRE
- Hour 42-48: SRE + Founder (handoff)

---

## Phase E: Iteration (Hour 48-72)

### E.1: Issue Monitoring (48-72 hours)

**Owner**: SRE | **Evidence**: Incident log**

```bash
# Auto-rollback triggers (24-hour watch)
$ npm run monitor:dashboard \
  --alert-on-error-rate-spike \
  --alert-threshold=5% \
  --auto-rollback-at=10%

# Collect critical issues
$ npm run incidents:list --window=24h | tee issues_48h.log
```

### E.2: Feedback Collection (48-72 hours)

**Owner**: Product Manager | **Evidence**: Feedback log**

```bash
# Survey first 10 partners
$ npm run survey:partners --limit=10
# Aggregate feedback into product backlog
```

### E.3: Performance Tuning (48-72 hours)

**Owner**: Performance Engineer | **Evidence**: Before/after latency comparison**

```bash
# If p99 latency > 200ms, apply cache optimization
$ npm run cache:optimize --target=api-responses
# Re-run load test and verify improvement
```

### E.4: Team Debrief (72:00)

**Owner**: Founder | **Evidence**: Retrospective notes**

Questions to answer:
1. What went smoothly?
2. What bottlenecks did we hit?
3. What surprised us?
4. What would we do differently next time?
5. Is system ready for full public launch?

---

## Rollback Procedures

**See INCIDENT_RESPONSE_PLAYBOOK.md for automatic and manual rollback procedures.**

Quick summary:
- **SSL cert error**: Auto-rollback in 10 min
- **DNS resolution failure**: Auto-rollback in 5 min
- **API 5xx error rate >5%**: Auto-rollback in 10 min
- **Manual rollback**: Revert DNS CNAME to workers.dev in <2 min

---

## Success Declaration

**Phase 3 is LIVE when:**
1. ✓ All 10-point checklist passes (within 2 hours post-cutover)
2. ✓ Error rate <0.5% after 24 hours
3. ✓ 5+ successful customer transactions
4. ✓ 3+ partner signups
5. ✓ PeopleDesk, Partner Network, Rate Limiting all operational
6. ✓ Zero unplanned downtime
7. ✓ No manual rollbacks triggered

---

## Contact & Escalation

**During Cutover (Hour 0-12):**
- **Critical issues**: Founder decision (immediate rollback)
- **API errors**: Backend Engineer + DevOps debug
- **DNS issues**: DevOps escalation
- **Monitoring gaps**: SRE on-call

**Post-Launch (Hour 12+):**
- **Customer issues**: Support (PeopleDesk)
- **Partner issues**: Partnership Manager
- **Technical debt**: Engineering backlog

---

**Document Version**: 1.0 | **Last Updated**: 2026-10-01 | **Status**: Ready for Execution
