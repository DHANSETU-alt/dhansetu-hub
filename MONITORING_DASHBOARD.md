# Phase 3 Monitoring Dashboard
**Real-Time KPI Tracking & Alert Configuration**

---

## Dashboard Overview

This document defines all monitoring dashboards, KPIs, and auto-alert triggers for Phase 3 go-live.

**Primary Dashboard**: https://app.datadoghq.com/dashboard/phase3-golive (auto-updated, 30-sec refresh)

---

## Key Performance Indicators (KPIs)

### Tier 1: Critical System Health (🔴 Red Alert if ANY fails)

| KPI | Target | Yellow | Red | Monitoring |
|-----|--------|--------|-----|-----------|
| **API Uptime** | 99.95%+ | <99.5% | <99% | Continuous |
| **Error Rate** | <0.5% | 1-2% | >5% | Every 30 sec |
| **DNS Resolution** | 100% | 95-99% | <95% | Every 30 sec |
| **SSL Certificate** | Valid | < 7 days to expiry | Expired/Invalid | Every 30 sec |
| **Database Connectivity** | 100% | 95-99% | <95% | Every 30 sec |
| **OAuth Health** | 100% | 95-99% | <95% | Every 30 sec |
| **Payment Processing** | 100% | 95-99% | <95% | Every 30 sec |

---

### Tier 2: Performance Metrics (⚠️ Yellow Alert on deviation)

| KPI | Target | Yellow | Red | Monitoring |
|-----|--------|--------|-----|-----------|
| **API Response Time (p50)** | <50ms | 75-100ms | >150ms | Every 30 sec |
| **API Response Time (p95)** | <100ms | 150-200ms | >300ms | Every 30 sec |
| **API Response Time (p99)** | <200ms | 250-300ms | >500ms | Every 30 sec |
| **Rate Limiting Effectiveness** | 0% false positives | 0.1-0.5% | >1% | Every 5 min |
| **Feature Flag Activation** | 100% | 95-99% | <95% | On deployment |
| **Cache Hit Rate** | >85% | 70-85% | <70% | Every 5 min |

---

### Tier 3: Business Metrics (📊 Track for optimization)

| KPI | Target | Monitoring Frequency |
|-----|--------|----------------------|
| **Transactions Processed** | >50/hour | Every hour |
| **Successful Payments** | >95% | Every 30 min |
| **Failed Transactions** | <5% | Every 30 min |
| **Revenue Generated** | ₹[TARGET]/day | Every hour |
| **Partner Signups** | >3/day | Every day |
| **Support Tickets Created** | >5/day | Every day |

---

## Real-Time Dashboard Layout

### Main Dashboard (URL: https://app.datadoghq.com/dashboard/phase3-golive)

**Refresh Rate**: 30 seconds (auto)  
**Viewable by**: All team members  
**Update source**: Datadog API (real-time)

#### Section 1: System Health (Top Left)

```
┌─────────────────────────────────────────────────────┐
│ PHASE 3 SYSTEM HEALTH (Last 24 hours)             │
├─────────────────────────────────────────────────────┤
│                                                     │
│ API Uptime:              ████████░  99.8% ✅        │
│ Error Rate:              ░░░░░░░░░░  0.3% ✅        │
│ DNS Resolution:          ██████████ 100% ✅        │
│ Database Connectivity:   ██████████ 100% ✅        │
│ SSL Certificate:         ██████████ Valid ✅       │
│ Payment Processing:      █████████░  98.7% ✅      │
│                                                     │
│ Overall Status: 🟢 HEALTHY                        │
│ Last updated: [TIMESTAMP]                          │
└─────────────────────────────────────────────────────┘
```

#### Section 2: Real-Time Metrics (Top Right)

```
┌─────────────────────────────────────────────────────┐
│ REAL-TIME PERFORMANCE (Last 5 minutes)             │
├─────────────────────────────────────────────────────┤
│                                                     │
│ API Response Time (p50):     [45ms] ✅             │
│ API Response Time (p95):     [95ms] ✅             │
│ API Response Time (p99):     [180ms] ✅            │
│                                                    │
│ Request Rate:                [1,250 req/min] ✅   │
│ Error Rate:                  [0.2%] ✅            │
│ Rate Limited:                [0.1%] ✅            │
│                                                    │
│ Peak Load:                   [CPU: 45% | RAM: 62%] │
│ Cache Hit Rate:              [88%] ✅             │
│                                                    │
└─────────────────────────────────────────────────────┘
```

#### Section 3: Business Metrics (Bottom Left)

```
┌─────────────────────────────────────────────────────┐
│ BUSINESS METRICS (This 24-hour window)             │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Transactions Processed:      [847] ✅              │
│ Successful Payments:         [805 / 847] 95%      │
│ Failed Transactions:         [42 / 847] 5%        │
│                                                    │
│ Revenue Generated:           ₹[45,200] 📈          │
│ Avg Transaction Value:       ₹[53.42]             │
│                                                    │
│ Partner Signups:             [12] 📊              │
│ Support Tickets:             [34] 📋              │
│ Customer Satisfaction:       [4.8/5.0] ⭐⭐⭐⭐  │
│                                                    │
└─────────────────────────────────────────────────────┘
```

#### Section 4: Alert Status (Bottom Right)

```
┌─────────────────────────────────────────────────────┐
│ ACTIVE ALERTS (Last 24 hours)                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│ 🟢 No critical alerts                              │
│                                                     │
│ ⚠️ 3 resolved alerts (auto-fixed):                │
│    • [10:30 UTC] High memory usage (normalized)    │
│    • [14:45 UTC] Rate limit spike (controlled)     │
│    • [19:20 UTC] Cache miss increase (recovered)   │
│                                                    │
│ Total incidents: 3                                 │
│ Auto-resolved: 3 (100%)                            │
│ Manual intervention: 0                             │
│                                                    │
└─────────────────────────────────────────────────────┘
```

---

## Alert Configuration (Datadog)

### Alert 1: High Error Rate (Auto-Escalation)

**Condition**: Error rate > 2% for 2 minutes  
**Severity**: HIGH  
**Action**: 
1. Slack #phase3-golive (immediate)
2. Page on-call engineer (5 min if unresolved)

```
Query: (trace.web.request.errors/trace.web.request)*100 > 2
Window: 5 minutes
Threshold: 2 minute breach
Recipients: @phase3-team, @oncall-engineer
```

---

### Alert 2: Critical Error Rate (Auto-Rollback Trigger)

**Condition**: Error rate > 5% for 10 minutes  
**Severity**: CRITICAL  
**Action**: 
1. SMS to Founder (immediate)
2. Auto-rollback to workers.dev (10-min countdown)
3. Incident bridge auto-created

```
Query: (trace.web.request.errors/trace.web.request)*100 > 5
Window: 10 minutes
Threshold: Auto-rollback if sustained
Recipients: @founder (SMS), @all-oncall
```

---

### Alert 3: High Latency (p99 > 200ms)

**Condition**: p99 latency > 200ms for 3 minutes  
**Severity**: MEDIUM  
**Action**: Slack notification + performance team page

```
Query: trace.web.request.duration.p99 > 200ms
Window: 3 minutes
Threshold: 200ms
Recipients: @performance-team
```

---

### Alert 4: DNS Resolution Failure

**Condition**: Domain not resolving for 30 seconds  
**Severity**: CRITICAL  
**Action**: 
1. SMS to DevOps lead (immediate)
2. Auto-rollback to workers.dev (5-min countdown)

```
Query: dns_resolution_success == 0
Window: 30 seconds
Threshold: Immediate escalation
Recipients: @devops-lead (SMS), @founder
```

---

### Alert 5: Database Connection Failure

**Condition**: Cannot connect to shakthi.db for 1 minute  
**Severity**: CRITICAL  
**Action**: 
1. Slack alert + SMS
2. Failover attempt or auto-rollback (5-min countdown)

```
Query: database_connection_success == 0
Duration: 1 minute
Threshold: Immediate escalation
Recipients: @dba, @backend-team
```

---

### Alert 6: Payment Processing Failure

**Condition**: Razorpay webhook failures >5 consecutive  
**Severity**: CRITICAL  
**Action**: 
1. SMS to Founder + Payment team (immediate)
2. Immediate manual rollback if not resolved in 2 min

```
Query: razorpay_webhook_failure_count > 5
Window: 2 minutes
Threshold: Immediate human intervention
Recipients: @founder (SMS), @payment-team (SMS)
```

---

### Alert 7: Rate Limiting Over-Aggressive

**Condition**: Blocking >10% of legitimate traffic  
**Severity**: HIGH  
**Action**: Disable rate limiting + investigate false positives

```
Query: rate_limit_blocks / total_requests > 10%
Window: 2 minutes
Threshold: Auto-disable if sustained
Recipients: @backend-team
```

---

### Alert 8: Feature Flag Deployment Failure

**Condition**: Feature flag deployment fails  
**Severity**: HIGH  
**Action**: Revert flag + investigate

```
Query: feature_flag_deployment_status == failed
Window: Immediate
Threshold: Block deployment until fixed
Recipients: @feature-flag-team
```

---

## Dashboard Queries (Copy-Paste Ready)

### Query 1: Error Rate Trend (Last 24h)

```
# Datadog query
(sum:trace.web.request.errors{env:prod} / sum:trace.web.request{env:prod}) * 100

# Expected output
2026-10-01 00:00 UTC: 0.1%
2026-10-01 04:00 UTC: 0.3%
2026-10-01 08:00 UTC: 0.2% (cutover window - slightly higher)
2026-10-01 12:00 UTC: 0.15%
2026-10-01 16:00 UTC: 0.12%
2026-10-01 20:00 UTC: 0.1%
```

### Query 2: API Latency by Percentile

```
# Datadog query
{
  p50: trace.web.request.duration.p50{env:prod},
  p95: trace.web.request.duration.p95{env:prod},
  p99: trace.web.request.duration.p99{env:prod}
}

# Expected output (in milliseconds)
p50: ~45ms (target: <50ms)
p95: ~95ms (target: <100ms)
p99: ~180ms (target: <200ms)
```

### Query 3: Uptime Percentage

```
# Datadog query
(1 - (sum:trace.web.request.errors / sum:trace.web.request)) * 100

# Expected output
99.8% (target: >99.5%)
```

### Query 4: Transaction Success Rate

```
# Datadog query
(sum:razorpay.transaction.success / sum:razorpay.transaction.total) * 100

# Expected output
95.3% (target: >95%)
```

### Query 5: Request Rate (RPS)

```
# Datadog query
sum:trace.web.request{env:prod}.as_rate(1m)

# Expected output
Baseline: ~500-1,000 requests/minute
Peak (cutover): ~1,500-2,000 requests/minute
Stable: ~800-1,200 requests/minute
```

---

## Monitoring Checklist (Hourly During Cutover)

**Owner**: SRE / Monitoring  
**Frequency**: Every hour during Hour 6-24

```
Hour: _______ UTC

CRITICAL METRICS:
[_] Uptime: ______% (target: >99.5%)
[_] Error rate: ______% (target: <0.5%)
[_] API latency (p99): ______ms (target: <200ms)
[_] Database: [Connected / Failed]
[_] DNS: [Resolving / Failed]
[_] SSL Cert: [Valid / Invalid]
[_] Payments: ______% success rate (target: >95%)

BUSINESS METRICS:
[_] Transactions this hour: _______
[_] Revenue this hour: ₹_______
[_] Partner signups: _______
[_] Support tickets: _______

ALERTS THIS HOUR:
[_] None
[_] Yes - describe: _________________________________

ACTIONS TAKEN:
[_] None
[_] Yes - describe: _________________________________

FORECAST NEXT HOUR:
Status: [Nominal / Caution / Alert]
Trending: [Stable / Improving / Degrading]
Notes: _________________________________________________

Signed: _________________ | Time: _______ UTC
```

---

## On-Call Runbook (During Monitoring)

### If Error Rate Alert Fires

```
1. CHECK ALERT DETAILS
   What: Error rate exceeded threshold
   When: [TIMESTAMP]
   Where: [Service/endpoint]
   Magnitude: [X]%

2. INVESTIGATE ROOT CAUSE (2 min)
   □ Check recent deployments: git log --oneline -10
   □ Check recent config changes: grep -r "ERROR" logs/*
   □ Check error types: What errors are occurring?
   □ Check affected endpoints: Which APIs are failing?

3. IMMEDIATE MITIGATION (if critical)
   □ If rollback needed: npm run deploy:rollback --target=workers.dev
   □ If specific feature broken: npm run feature-flags:set --flag=X --status=disabled
   □ If config issue: Fix config + reload

4. VERIFY FIX
   □ Check error rate dropped
   □ Run 5-minute test to ensure stable

5. POST-INCIDENT
   □ Document in INCIDENT_LOG.txt
   □ Schedule post-mortem
   □ Notify Founder + team
```

### If Latency Alert Fires

```
1. IDENTIFY BOTTLENECK
   □ Is it DB query latency? Check PRAGMA query_plan
   □ Is it network latency? Check Cloudflare metrics
   □ Is it API processing? Check trace spans in Datadog

2. OPTIMIZE (if possible)
   □ Enable caching if not already
   □ Optimize slow queries
   □ Add rate limiting to prevent overload

3. VERIFY IMPROVEMENT
   □ Run load test
   □ Check p50, p95, p99 latencies
   □ Ensure SLA restored

4. DOCUMENT
   □ What was the issue?
   □ How did we fix it?
   □ What should we monitor differently?
```

### If Database Alert Fires

```
1. VERIFY CONNECTION STATUS
   $ sqlite3 shakthi.db "SELECT 1"
   Expected: 1

2. CHECK DATABASE INTEGRITY
   $ sqlite3 shakthi.db "PRAGMA integrity_check;"
   Expected: ok

3. IF CORRUPTED
   □ Restore from backup
   □ Database backup location: [PATH]
   □ Estimated restore time: [X] minutes

4. IF CONNECTION ISSUE
   □ Check filesystem permissions: ls -l shakthi.db
   □ Check disk space: df -h
   □ Restart database process if needed

5. VERIFY CONNECTIVITY RESTORED
   □ Run health check: npm run health:database
   □ Expected: "ok"
```

---

## Post-Cutover Monitoring (First 72 Hours)

### Day 1 Targets (Hour 0-24)

| Metric | Hour 0-6 | Hour 6-12 | Hour 12-24 | Status |
|--------|----------|-----------|-----------|--------|
| Uptime | 99.5%+ | 99.7%+ | 99.9%+ | [✓/✗] |
| Error rate | <2% | <1% | <0.5% | [✓/✗] |
| Latency p99 | <250ms | <220ms | <200ms | [✓/✗] |
| Payments | >90% | >93% | >95% | [✓/✗] |

### Day 2 Targets (Hour 24-48)

| Metric | Target | Status |
|--------|--------|--------|
| Uptime | >99.9% | [✓/✗] |
| Error rate | <0.5% | [✓/✗] |
| Latency p99 | <200ms | [✓/✗] |
| Transactions | >50/hour | [✓/✗] |
| Payment success | >95% | [✓/✗] |

### Day 3 Targets (Hour 48-72)

| Metric | Target | Status |
|--------|--------|--------|
| Uptime | >99.9% | [✓/✗] |
| Error rate | <0.5% | [✓/✗] |
| Latency p99 | <200ms | [✓/✗] |
| Transactions | >75/hour | [✓/✗] |
| Payment success | >96% | [✓/✗] |
| Partner signups | ≥3 | [✓/✗] |

---

## Custom Dashboards (URLs)

**Main Dashboard**: https://app.datadoghq.com/dashboard/phase3-golive  
**Error Analysis**: https://app.datadoghq.com/dashboard/phase3-errors  
**Payment Metrics**: https://app.datadoghq.com/dashboard/razorpay-flow  
**Partner Network**: https://app.datadoghq.com/dashboard/partner-network  
**Infrastructure**: https://app.datadoghq.com/dashboard/cloudflare-workers  
**Business Metrics**: https://app.datadoghq.com/dashboard/revenue-tracking  

---

## Slack Integrations

**Primary Channel**: #phase3-golive  
**Alert Routing**: Auto-posts all critical alerts  
**Notification Format**:

```
🚨 [ALERT] Error Rate High
Service: API
Severity: HIGH
Value: 2.3% (threshold: 2%)
Duration: 2 min
Graph: [Datadog link]
Action: Investigating...

Timestamp: 2026-10-01 08:15:30 UTC
```

---

## Escalation Thresholds

| Condition | Wait Time | Action |
|-----------|-----------|--------|
| Error rate 1-2% | 5 min | Alert, investigate |
| Error rate 2-5% | 3 min | Alert, begin fix |
| Error rate >5% | 10 min | Auto-rollback or manual intervention |
| Error rate >10% | 0 min | Immediate rollback |
| DNS fails | 30 sec | Alert, 5 min to rollback |
| Payment fails (100%) | 2 min | Immediate rollback |
| SSL cert error | 1 min | Alert, 10 min to rollback |
| Database fails | 30 sec | Alert, 5 min to failover/rollback |

---

## Weekly Report Template

**Owner**: SRE / Analytics  
**Frequency**: Every Monday for 4 weeks post-launch

```
# Phase 3 Weekly Monitoring Report

**Week**: [W/C DATE]
**Period**: Hour [X] - [Y] of go-live

## Summary
- Uptime: ______%
- Error rate: ______%
- Transactions: _______
- Revenue: ₹_______

## Incidents
[List any incidents, root causes, resolutions]

## Performance Trends
- Latency: [Improving / Stable / Degrading]
- Errors: [Improving / Stable / Degrading]
- Throughput: [Increasing / Stable / Decreasing]

## Optimizations Applied
- [Change 1]
- [Change 2]

## Next Week Focus
- [Priority 1]
- [Priority 2]
```

---

**Document Version**: 1.0 | **Last Updated**: 2026-10-01 | **Status**: Ready for Deployment
