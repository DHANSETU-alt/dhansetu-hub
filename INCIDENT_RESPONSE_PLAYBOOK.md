# Phase 3 Incident Response Playbook
**Automatic Rollback Procedures & Crisis Management**

---

## Executive Summary

This playbook defines **automatic and manual rollback procedures** for Phase 3 go-live. If any critical condition is detected, the system automatically reverts to `dhansetuhub.workers.dev` within the specified time window.

**Philosophy**: Better to rollback fast and investigate later than to burn customer trust.

---

## Automatic Rollback Triggers

| Trigger | Threshold | Detection Window | Auto-Rollback Time | Action |
|---------|-----------|------------------|--------------------|--------|
| **SSL Certificate Error** | Certificate invalid/expired | Continuous | 10 minutes | Revert DNS CNAME |
| **DNS Resolution Failure** | Domain not resolving | 30 sec check interval | 5 minutes | Revert DNS A record |
| **API 5xx Errors** | >5% of requests | 5-minute window | 10 minutes | Revert Workers deployment |
| **Database Connectivity** | Cannot connect to shakthi.db | Continuous | 5 minutes | Failover to backup DB |
| **OAuth/Razorpay Failures** | 100% failure rate on payments | 2-minute window | Immediate (2 min) | Revert to workers.dev |
| **Rate Limiting Over-aggressive** | Blocking >10% legitimate traffic | 5-minute window | 10 minutes | Disable rate limiting |
| **Memory/CPU Exhaustion** | >95% utilization on Workers | 2-minute window | 5 minutes | Scale down or revert |

---

## Rollback Decision Matrix

### Low Severity (Manual Intervention Only)

**Symptoms**: Performance degradation, partial feature unavailability

**Response Time**: 30 minutes

- [ ] Investigate root cause
- [ ] Determine if rollback is necessary
- [ ] If yes, execute manual rollback (see Manual Rollback section)
- [ ] If no, implement targeted fix

**Examples**:
- Latency spike to 250ms (target: 200ms)
- Single feature flag causing errors
- Cache miss rate increase

---

### Medium Severity (Automatic Rollback in 10 min)

**Symptoms**: System mostly working but experiencing elevated errors

**Response Time**: Automatic after 10 minutes

- [ ] Monitoring system detects condition
- [ ] Alert fires to #phase3-golive Slack channel
- [ ] Team has 10 minutes to override rollback (by updating trigger threshold)
- [ ] If no override, automatic rollback executes
- [ ] Post-rollback investigation begins

**Examples**:
- API error rate 2-5%
- Response time 200-500ms (p99)
- Rate limiting blocking >5% traffic

---

### Critical Severity (Automatic Rollback in 5 min)

**Symptoms**: System severely degraded or unavailable

**Response Time**: Automatic after 5 minutes

- [ ] Monitoring detects critical failure
- [ ] Immediate Slack/SMS alert to Founder
- [ ] All on-call engineers notified
- [ ] If no manual intervention within 5 min, automatic rollback
- [ ] Incident post-mortem scheduled

**Examples**:
- DNS resolution failures
- Database connection failures
- OAuth/Payment processing 100% failure rate

---

### Critical Severity (Immediate Rollback)

**Symptoms**: System completely down or security breach

**Response Time**: Immediate (within 2 minutes)

- [ ] Automatic rollback executes immediately
- [ ] No wait period, no override option
- [ ] Founder notified via SMS + Slack
- [ ] Emergency incident bridge scheduled

**Examples**:
- SSL certificate error (invalid/expired)
- Payment system breach detected
- Complete API outage (>10 seconds unresponsive)

---

## Automatic Rollback Procedures

### Rollback Trigger 1: SSL Certificate Error (10-min auto-rollback)

**Detection**: Continuous monitoring of SSL cert validity

```bash
# Monitoring script (runs every 30 seconds)
$ npm run monitor:ssl-cert --alert-on-invalid

# Detection log:
# [2026-10-01 08:15:30] ✗ SSL cert INVALID - expires 2024-12-01
# [2026-10-01 08:16:00] ✗ SSL cert still INVALID
# ... (continues checking every 30 seconds)
# [2026-10-01 08:25:00] SSL cert INVALID for 10 minutes - ROLLBACK TRIGGERED
```

**Automatic Rollback Action (executes at 10-min mark)**:

```bash
# 1. Alert Founder + Team (immediate)
$ npm run alert:critical --message="SSL Certificate Error - Rolling back to workers.dev"

# 2. Revert DNS CNAME to workers.dev
$ curl -X PATCH "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${RECORD_ID_A}" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "CNAME",
    "name": "@",
    "content": "dhansetuhub.workers.dev",
    "ttl": 300
  }' | tee ssl_cert_rollback.log

# 3. Verify rollback completed
$ dig dhansetuhub.in | grep CNAME
# Expected: CNAME dhansetuhub.workers.dev

# 4. Document incident
$ echo "SSL cert rollback at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> INCIDENT_LOG.txt
$ echo "Reason: Certificate invalid/expired" >> INCIDENT_LOG.txt
$ echo "Action: Auto-rollback to workers.dev" >> INCIDENT_LOG.txt

# 5. Schedule incident post-mortem
$ npm run incident:schedule-postmortem --title="SSL Cert Error During Go-Live" --time="+1h"
```

---

### Rollback Trigger 2: DNS Resolution Failure (5-min auto-rollback)

**Detection**: Every 30 seconds, verify domain resolves

```bash
# Monitoring script
$ npm run monitor:dns-resolution --check-interval=30s

# If DNS fails to resolve for 5 minutes:
# [2026-10-01 08:30:00] ✗ DNS resolution FAILED for dhansetuhub.in
# [2026-10-01 08:30:30] ✗ DNS still failing
# ... (continues)
# [2026-10-01 08:35:00] DNS failed for 5 minutes - ROLLBACK TRIGGERED
```

**Automatic Rollback Action**:

```bash
# 1. Alert team (SMS + Slack)
$ npm run alert:critical --channel=sms --message="DNS FAIL - Rolling back"

# 2. Revert DNS record
$ curl -X PATCH "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${RECORD_ID_A}" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "A",
    "name": "@",
    "content": "104.21.28.1",
    "ttl": 300
  }' | tee dns_rollback.log

# 3. Verify resolution works
$ dig dhansetuhub.in +short
# Should resolve to Cloudflare IP or workers.dev

# 4. Document
$ echo "DNS rollback executed at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> INCIDENT_LOG.txt
```

---

### Rollback Trigger 3: API 5xx Error Rate >5% (10-min auto-rollback)

**Detection**: Real-time monitoring of error rates via Datadog

```bash
# Monitoring configuration
$ npm run monitor:error-rate \
  --threshold=5% \
  --window=5min \
  --alert-severity=high

# Example detection:
# [2026-10-01 08:45:00] Error rate 0.2% - OK
# [2026-10-01 08:45:30] Error rate 2.1% - OK
# [2026-10-01 08:46:00] Error rate 4.8% - OK
# [2026-10-01 08:46:30] Error rate 5.3% - ALERT (above threshold)
# [2026-10-01 08:47:00] Error rate 6.1% - ALERT
# [2026-10-01 08:50:00] Error rate 5.8% - ALERT (sustained for 3+ min)
# [2026-10-01 08:56:00] Error rate 5.5% - ALERT (10 min sustained) - ROLLBACK
```

**Automatic Rollback Action**:

```bash
# 1. Alert team
$ npm run alert:critical --message="Error rate exceeded 5% for 10 min - Rolling back"

# 2. Begin rollback
$ npm run deploy:rollback --target=dhansetuhub.workers.dev \
  --git-hash=$(git log --oneline | head -1 | awk '{print $1}')

# 3. Verify Workers deployment is live
$ curl -s https://dhansetuhub.workers.dev/api/health | jq .status
# Expected: "ok"

# 4. Update DNS to workers.dev (if not already)
$ curl -X PATCH "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${RECORD_ID_A}" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"content": "dhansetuhub.workers.dev"}' \
  | tee api_error_rollback.log

# 5. Investigate root cause
$ npm run logs:recent --service=api --limit=1000 | grep ERROR | head -50

# 6. Document
$ echo "API error rate rollback at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> INCIDENT_LOG.txt
$ echo "Peak error rate: $(npm run metrics:error-rate --get-peak)" >> INCIDENT_LOG.txt
```

---

### Rollback Trigger 4: Database Connectivity Failure (5-min auto-rollback)

**Detection**: Health check to database every 30 seconds

```bash
# Monitoring
$ npm run monitor:database-health --check-interval=30s

# Detection:
# [2026-10-01 09:00:00] DB connection OK (response: 45ms)
# [2026-10-01 09:00:30] DB connection FAILED - retrying
# [2026-10-01 09:01:00] DB connection FAILED - retrying
# ... (continues for 5 minutes)
# [2026-10-01 09:05:00] DB connection failed for 5 min - ROLLBACK
```

**Automatic Rollback Action**:

```bash
# 1. Alert team - CRITICAL
$ npm run alert:critical --message="Database unreachable - Immediate rollback"

# 2. Failover to backup database (if configured)
$ npm run database:failover --target=backup-db

# 3. If failover fails, revert to workers.dev
$ npm run deploy:rollback --target=dhansetuhub.workers.dev

# 4. Update DNS
$ curl -X PATCH "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${RECORD_ID_A}" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"content": "dhansetuhub.workers.dev"}' \
  | tee database_rollback.log

# 5. Investigate
$ sqlite3 shakthi.db "PRAGMA integrity_check;" | head -5
$ ls -lh shakthi.db

# 6. Document
$ echo "Database rollback at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> INCIDENT_LOG.txt
$ echo "Last successful connection: $(npm run metrics:db-last-success)" >> INCIDENT_LOG.txt
```

---

### Rollback Trigger 5: OAuth/Razorpay Failures (Immediate - 2 min)

**Detection**: 100% failure rate on auth/payment endpoints for 2 minutes

```bash
# Monitoring
$ npm run monitor:auth-health --check-interval=30s
$ npm run monitor:payment-health --check-interval=30s

# Detection example:
# [2026-10-01 09:15:00] Google OAuth: OK
# [2026-10-01 09:15:30] Google OAuth: FAILED (auth endpoint unreachable)
# [2026-10-01 09:16:00] Google OAuth: FAILED
# [2026-10-01 09:16:30] Google OAuth: FAILED
# [2026-10-01 09:17:00] Google OAuth: FAILED (100% fail rate for 2 min) - IMMEDIATE ROLLBACK
```

**Automatic Rollback Action (IMMEDIATE - NO WAIT)**:

```bash
# 1. SMS alert to Founder (immediate)
$ npm run alert:critical --via=sms --message="Auth/Payment failure - rolling back NOW"

# 2. Immediate DNS revert
$ curl -X PATCH "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${RECORD_ID_A}" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"content": "dhansetuhub.workers.dev"}' \
  | tee auth_rollback_immediate.log

# 3. Verify rollback
$ curl -s https://dhansetuhub.in/api/auth/google/callback 2>&1 | head -5

# 4. Emergency incident bridge (auto-scheduled)
$ npm run incident:emergency-bridge --start-in=5min

# 5. Document critical incident
$ echo "CRITICAL: Auth/Payment rollback at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> INCIDENT_LOG.txt
$ echo "Reason: 100% payment processing failure" >> INCIDENT_LOG.txt
```

---

## Manual Rollback Procedures

### When to Execute Manual Rollback

Execute manual rollback if:
1. Automatic rollback failed to trigger correctly
2. System is partially working but experiencing cascading failures
3. Business decision to temporarily revert while investigating

### Manual Rollback Steps (Commander: Founder)

**Estimated time**: 5-10 minutes from decision to full revert

```bash
# STEP 1: ANNOUNCE (Immediately)
# Post to #phase3-golive Slack:
# "🔴 INITIATING MANUAL ROLLBACK - Rolling back to workers.dev"
# Notify team via SMS if critical

# STEP 2: VERIFY WORKERS.DEV IS HEALTHY
$ curl -s https://dhansetuhub.workers.dev/api/health | jq .status
# Expected: "ok"

# If workers.dev is also down:
#   - Publish status page message: "We're experiencing service disruption"
#   - Activate incident response bridge
#   - Escalate to Cloudflare/infrastructure team

# STEP 3: REVERT DNS IMMEDIATELY
$ CURRENT_DNS=$(dig dhansetuhub.in +short | head -1)
$ echo "Current DNS target: $CURRENT_DNS"

$ curl -X PATCH "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${RECORD_ID_A}" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "CNAME",
    "name": "@",
    "content": "dhansetuhub.workers.dev",
    "ttl": 300,
    "proxied": true
  }' | jq '.result | {id, name, type, content, ttl}' | tee rollback_dns_change.json

# Expected response:
#  {
#    "id": "...",
#    "name": "@",
#    "type": "CNAME",
#    "content": "dhansetuhub.workers.dev",
#    "ttl": 300
#  }

# STEP 4: VERIFY ROLLBACK
$ sleep 10

$ dig dhansetuhub.in CNAME +short
# Expected: "dhansetuhub.workers.dev"

$ curl -s -L https://dhansetuhub.in/ | head -20
# Expected: Should show workers.dev homepage

# STEP 5: CONFIRM ROLLBACK SUCCESSFUL
$ echo "✓ DNS rollback confirmed at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> ROLLBACK_LOG.txt

# STEP 6: DISABLE PROBLEMATIC FEATURE FLAGS (if needed)
# If specific feature caused rollback:
$ npm run feature-flags:set --flag=PeopleDesk --status=disabled
$ npm run feature-flags:set --flag=PartnerNetwork --status=disabled
$ npm run feature-flags:set --flag=RateLimiting --status=disabled

# STEP 7: POST-ROLLBACK UPDATES
# Update status page
$ npm run status-page:update --message="We've rolled back to our stable infrastructure while we investigate. Services should be restored in 30 minutes."

# Send customer notification
$ npm run email:send-template --template=service_incident --audience=all

# STEP 8: SCHEDULE INCIDENT INVESTIGATION
$ npm run incident:schedule-postmortem --title="Phase 3 Rollback" --time="+1h"

# STEP 9: DOCUMENT INCIDENT
$ cat > incident_summary_$(date +%Y%m%d_%H%M%S).md <<EOF
# Phase 3 Rollback Incident Report

**Incident Time**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
**Duration of Outage**: _______ minutes
**Reason for Rollback**: _________________________
**Root Cause**: _________________________
**Resolution**: Rolled back to workers.dev

## Timeline
- [T+0] Incident detected
- [T+X] Rollback initiated
- [T+Y] DNS reverted
- [T+Z] Services restored

## Impact
- Customers affected: _______
- Transactions failed: _______
- Revenue impacted: ₹_______

## Action Items
1. Investigate root cause
2. Implement fix
3. Re-test in staging
4. Attempt re-deployment

## Owner
- Incident Commander: _______
- Technical Lead: _______
- Post-Mortem Lead: _______
EOF
```

---

## Incident Response Bridge

**Automatic Scheduling**:
- Triggered by: Critical incident (rollback)
- Bridge link: Google Meet (auto-created)
- Participants: Auto-invited (Founder, all on-call engineers)
- Frequency: Every 15 minutes until resolved

**Bridge Agenda**:
1. Status update (current state, metrics)
2. Root cause hypothesis
3. Immediate actions (fix or re-attempt)
4. Escalations (if needed)
5. Communication to customers

---

## Post-Rollback Recovery Plan

### Phase 1: Investigation (0-30 min post-rollback)

```bash
# 1. Collect logs
$ npm run logs:export --service=all --timerange="-2h" --format=json | tee logs_post_rollback.json

# 2. Identify root cause
$ npm run logs:analyze --query="ERROR" | head -100

# 3. Correlate with metrics
$ npm run metrics:export --timerange="-2h" | jq '.errors, .latency'

# 4. Create runbook for fix
$ cat > ROLLBACK_RECOVERY_RUNBOOK.md <<EOF
# Recovery Plan

**Issue**: [Describe what broke]
**Root Cause**: [Explain why]
**Fix**: [Step-by-step fix]
**Testing**: [How to validate fix]
**Re-deployment**: [When/how to retry]
EOF
```

### Phase 2: Fix & Testing (30-120 min post-rollback)

```bash
# 1. Implement fix
$ git checkout -b fix/phase3-incident-[issue-name]
$ [make code changes]
$ git add -A
$ git commit -m "Fix: [description of issue and fix]"

# 2. Run full test suite
$ npm run test:all --project=phase3
Expected: All tests pass

# 3. Load test the fix
$ npm run load-test --target=https://dhansetuhub.workers.dev --duration=30m

# 4. Staging validation
$ npm run deploy:staging
$ npm run test:integration --target=staging

# 5. Get approval from team lead
$ npm run pr:create --title="Fix: Phase 3 incident - [description]"
$ [wait for review & approval]
```

### Phase 3: Re-deployment Attempt (if root cause fixed)

```bash
# 1. Verify readiness
$ ./verify_domain_infrastructure.sh
# Expected: READY FOR CUTOVER

# 2. Follow PHASE3_COMPRESSED_GOLIVE.md steps from beginning
# But this time, team has full context of what failed
```

---

## Incident Communication Templates

### To Team (Slack)

**On Rollback**:
```
🔴 ROLLBACK INITIATED - Phase 3 has been rolled back to workers.dev

Reason: [Brief description]
Time: [Timestamp]
Impact: Services are operating normally on workers.dev

Next Steps:
- Investigation bridge in 5 minutes
- Target resolution: [timeframe]
- Updates every 15 minutes

Bridge link: [Google Meet URL]
```

**Post-Resolution**:
```
✅ RESOLVED - Phase 3 issue has been fixed and tested

Fix: [Brief description of what was wrong and how it was fixed]
Re-deployment: [Scheduled time, or pending further testing]

Incident post-mortem: [Scheduled for X time]
```

### To Customers (Email)

**On Service Disruption**:
```
Subject: DhanSetu Hub Service Disruption - [HH:MM UTC]

We're aware of a service disruption affecting DhanSetu Hub. Our team is actively investigating and working to restore full service.

Current Status: Services operating on backup infrastructure
Expected Resolution: [Time]

We apologize for any inconvenience and appreciate your patience.

Support: support@dhansetuhub.in
Status Page: status.dhansetuhub.in
```

**On Resolution**:
```
Subject: DhanSetu Hub Service Restored ✓

The service disruption has been resolved. DhanSetu Hub is now operating normally.

What happened: [Brief, non-technical explanation]
Impact: [How many customers affected, ~duration]

We've implemented [X] to prevent this in the future.

Thank you for your patience and continued trust in DhanSetu Hub.
```

---

## Monitoring Dashboards (Real-Time)

**Auto-Rollback Status Dashboard**:
- URL: https://app.datadoghq.com/dashboard/phase3-rollback-status
- Shows: Current trigger status, time-to-rollback countdown, recent rollbacks
- Updates: Every 30 seconds

**Incident Response Bridge**:
- Google Meet link: [auto-generated per incident]
- Slack: #phase3-golive (pinned)
- Invite: All on-call engineers (automatic)

---

## Glossary

| Term | Definition |
|------|-----------|
| **Auto-Rollback** | Automatic reversion to workers.dev when trigger condition is met |
| **Manual Rollback** | Human-initiated reversion (Founder decision) |
| **Trigger** | Condition that causes rollback (e.g., error rate >5%) |
| **Detection Window** | Time monitoring must observe the condition before triggering rollback |
| **TTL** | Time-To-Live for DNS records (how long clients cache the result) |
| **CNAME** | Canonical Name record pointing domain to another domain |
| **Incident Bridge** | Real-time meeting for incident response team to coordinate |
| **Post-Mortem** | After-incident review to identify root cause and improvements |

---

## Testing Auto-Rollback (Non-Production)

To verify auto-rollback mechanisms work correctly, run test drills:

```bash
# TEST DRILL 1: Simulate high error rate
$ npm run test:error-rate-trigger --simulate-error-rate=10% --duration=5min
# Expected: Auto-rollback triggers after 10 minutes

# TEST DRILL 2: Simulate database failure
$ npm run test:database-trigger --simulate-failure=true --duration=5min
# Expected: Auto-rollback triggers after 5 minutes

# TEST DRILL 3: Simulate SSL cert error
$ npm run test:ssl-trigger --simulate-invalid-cert=true --duration=5min
# Expected: Auto-rollback triggers after 10 minutes

# Verify all test drills completed successfully
$ npm run test:rollback-drills --summary
```

---

## Escalation Chain

**If manual rollback fails**:
1. Contact Cloudflare support (priority queue)
2. Request emergency DNS support
3. Escalate to Founder for business decision

**If incident continues >1 hour**:
1. Schedule emergency board meeting
2. Prepare customer communication (major incident)
3. Activate 24/7 incident response (extended team)

---

**Document Version**: 1.0 | **Last Updated**: 2026-10-01 | **Status**: Ready for Execution
