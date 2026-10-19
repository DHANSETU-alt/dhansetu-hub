# Phase 3 Go-Live Master Index
**48-72 Hour Compressed Cutover - Complete Execution Framework**

---

## Quick Start for Founder

You have 5 production-ready documents that together form a **complete, executable go-live framework**. Follow this sequence:

### Before Cutover (Hour -24)
1. **Read**: PHASE3_COMPRESSED_GOLIVE.md (Understand the full plan)
2. **Verify**: Run `./verify_domain_infrastructure.sh` (Ensure readiness)
3. **Brief**: Share GOLIVE_CHECKLIST.md with team (Everyone tracks together)
4. **Review**: Read INCIDENT_RESPONSE_PLAYBOOK.md (Know what could go wrong)

### During Cutover (Hour 0-12)
1. **Execute**: Follow PHASE3_COMPRESSED_GOLIVE.md hour-by-hour
2. **Track**: Update GOLIVE_CHECKLIST.md in real-time (every task)
3. **Monitor**: Watch MONITORING_DASHBOARD.md (refresh every 30 sec)
4. **Communicate**: Use COMMUNICATION_TEMPLATES.md (send updates every hour)
5. **Respond**: Follow INCIDENT_RESPONSE_PLAYBOOK.md (if issues arise)

### After Cutover (Hour 12-72)
1. **Validate**: Complete C.1-C.5 checklists in GOLIVE_CHECKLIST.md
2. **Launch**: Execute Phase D (Marketing, outreach, announcements)
3. **Monitor**: Run hourly checks from MONITORING_DASHBOARD.md
4. **Debrief**: Team retrospective at Hour 72

---

## Document Reference

### 1. PHASE3_COMPRESSED_GOLIVE.md
**Purpose**: Minute-by-minute execution plan  
**Size**: ~500 lines | **Read time**: 45 min  
**Owner**: Founder (execution lead)

**Contains**:
- ✓ Executive summary (success criteria, timeline)
- ✓ Phase A: Pre-Cutover procedures (6 hours)
- ✓ Phase B: Parallel cutover (6 hours)
- ✓ Phase C: Validation (12 hours)
- ✓ Phase D: Full launch (24 hours)
- ✓ Phase E: Iteration (24 hours)
- ✓ Rollback procedures

**How to use**:
- Print and bring to cutover room
- Follow step-by-step during Hour 0-24
- Check off each task as completed
- Track exact timestamps

**Key sections**:
- B.4: Domain DNS Atomic Switch (THE critical 5-minute window)
- C.1: 10-Point Validation Checklist (must pass or rollback)
- D.1-D.5: Full launch sequence

---

### 2. GOLIVE_CHECKLIST.md
**Purpose**: Real-time tracking spreadsheet  
**Size**: ~400 lines | **Read time**: 20 min to understand structure  
**Owner**: QA Engineer (updates continuously)

**Contains**:
- ✓ Hour-by-hour task checklist (A.1 - E.5)
- ✓ Evidence fields (what to screenshot/document)
- ✓ Status rollup summaries
- ✓ Pass/fail decision points
- ✓ Final verdict template

**How to use**:
- Open in Google Docs or local editor
- Update in real-time as each task completes
- Timestamp everything (UTC)
- Take screenshots for evidence
- Use as go/no-go decision log

**Critical checkpoints**:
- Hour 4:30: All Phase A complete? → Proceed to B
- Hour 8:05: DNS cutover done? → Start monitoring
- Hour 14:00: 10-point checklist pass? → Proceed to launch
- Hour 24:00: All validations done? → Full launch

---

### 3. INCIDENT_RESPONSE_PLAYBOOK.md
**Purpose**: Automatic and manual rollback procedures  
**Size**: ~350 lines | **Read time**: 30 min  
**Owner**: DevOps/SRE (activation if needed)

**Contains**:
- ✓ Auto-rollback triggers (8 conditions)
- ✓ Detection thresholds and windows
- ✓ Automatic response procedures
- ✓ Manual rollback steps
- ✓ Post-rollback recovery plan
- ✓ Incident communication templates

**How to use**:
- Review before cutover (know the scenarios)
- Refer to during issues
- Follow the runbook for your specific incident
- Communicate using provided templates
- Schedule post-mortem immediately

**Rollback triggers**:
- SSL certificate error → 10-min auto-rollback
- DNS resolution failure → 5-min auto-rollback
- API 5xx error >5% → 10-min auto-rollback
- Database failure → 5-min auto-rollback
- OAuth/Payment 100% fail → Immediate rollback
- Rate limiting >10% → 10-min auto-rollback

**Most important section**:
- Manual Rollback Procedures (5-10 min to revert)

---

### 4. COMMUNICATION_TEMPLATES.md
**Purpose**: Pre-written notifications (copy-paste ready)  
**Size**: ~300 lines | **Read time**: 20 min  
**Owner**: Founder / Marketing Manager

**Contains**:
- ✓ 6 team communication templates
- ✓ 5 customer email templates
- ✓ 2 partner email templates
- ✓ 3 status page templates
- ✓ 2 escalation templates

**How to use**:
- Search for your scenario (e.g., "launch success")
- Copy exact template text
- Fill in bracketed fields [LIKE_THIS]
- Verify facts before sending
- Send to appropriate channel/audience

**Key templates**:
- Pre-cutover team standup (30 min before)
- Every-30-min status updates (during cutover)
- Successful cutover announcement (Hour 8:05)
- Validation checklist results (Hour 14)
- Launch success announcement (Hour 24)

**Send timing**:
- Hour 0:00 - Team standup
- Hour 6:00 - "Cutover starting" team message
- Hour 8:05 - "Atomic switch complete"
- Hour 14:00 - "Validation passed" + customer email
- Hour 24:00 - Launch announcement

---

### 5. MONITORING_DASHBOARD.md
**Purpose**: Real-time KPI tracking & alert configuration  
**Size**: ~350 lines | **Read time**: 30 min  
**Owner**: SRE / Monitoring

**Contains**:
- ✓ Key Performance Indicators (3 tiers)
- ✓ Real-time dashboard layout (what to watch)
- ✓ 8 auto-alert configurations (Datadog)
- ✓ Copy-paste dashboard queries
- ✓ Hourly monitoring checklist
- ✓ On-call runbooks (if alerts fire)
- ✓ Escalation thresholds
- ✓ Weekly report template

**How to use**:
- Open https://app.datadoghq.com/dashboard/phase3-golive
- Watch these 8 metrics continuously:
  1. API Uptime (target: >99.5%)
  2. Error Rate (target: <0.5%)
  3. API Latency p99 (target: <200ms)
  4. Database connectivity (target: 100%)
  5. DNS resolution (target: 100%)
  6. SSL certificate (target: valid)
  7. Payment success (target: >95%)
  8. Request rate (monitor for spikes)

**Auto-rollback if**:
- Error rate >5% for 10 min
- DNS fails for 5 min
- Database unreachable for 5 min
- Payment processing 100% fails for 2 min

**Dashboard refresh**: 30 seconds (auto)

---

## Execution Timeline

### PRE-CUTOVER (24 hours before)

```
Phase A: Pre-Cutover (Hour 0-6)
├── A.1: Final acceptance gate (30 min)
│   └── Run 5 checks, confirm "READY FOR CUTOVER"
├── A.2: Database backup + recovery test (1 hour)
│   └── Create backup, verify restore works
├── A.3: OAuth/Razorpay URL validation (30 min)
│   └── Test endpoints respond correctly
├── A.4: SSL certificate verification (15 min)
│   └── Verify cert is valid and expires in future
├── A.5: Load test (2 hours)
│   └── Test system can handle cutover traffic spike
└── A.6: Communication ready (15 min)
    └── Templates staged, team confirmed ready
```

### CUTOVER WINDOW (Hour 6-12) - CRITICAL

```
Phase B: Parallel Cutover (Hour 6-12)
├── B.1: DNS TTL reduction (30 min, START FIRST)
│   └── Reduce TTL to 300 sec, wait 10 min for propagation
├── B.2: Feature flag activation (30 min, parallel)
│   └── Enable PeopleDesk, Partner Network, Rate Limiting
├── B.3: Rate limiting gradual enable (1 hour, parallel)
│   └── Phases: 1 (light) → 2 (standard) → 3 (production)
├── B.4: ATOMIC DNS SWITCH (5 minutes, CRITICAL)
│   └── Point dhansetuhub.in → dhansetuhub.workers.dev
│   └── NO ROLLBACK AFTER THIS POINT
├── B.5: Monitoring startup (1 hour, parallel)
│   └── Start error rate, latency, revenue tracking
└── B.6: On-call team standby (entire 6-hour window)
    └── Updates every 30 min in Slack
```

### VALIDATION (Hour 12-24)

```
Phase C: Validation (Hour 12-24)
├── C.1: 10-point checklist (2 hours, MUST PASS)
│   └── 10 automated checks, all must pass
├── C.2: Real customer test (3 transactions, 3 hours)
│   └── Process 3 real end-to-end payments
├── C.3: PeopleDesk operations (3 hours)
│   └── Create, assign, resolve support ticket
├── C.4: Partner signup + commission (3 hours)
│   └── Test partner signup and commission calculation
└── C.5: Analytics verification (30 min)
    └── Verify GA4 and Razorpay events flowing
```

### FULL LAUNCH (Hour 24-48)

```
Phase D: Full Launch (Hour 24-48)
├── D.1: Marketing landing page live
├── D.2: Email campaign activation
├── D.3: Social media announcement
├── D.4: Customer outreach (3-email sequence)
└── D.5: 24/7 on-call rotation
```

### MONITORING & DEBRIEF (Hour 48-72)

```
Phase E: Iteration (Hour 48-72)
├── E.1: Issue monitoring (24 hours)
├── E.2: Feedback collection (first 10 partners)
├── E.3: Performance tuning (if needed)
└── E.4: Team debrief (lessons learned)
```

---

## Success Definition

**Phase 3 is LIVE when ALL of the following are true:**

1. ✅ **No unplanned downtime**
   - DNS cutover < 30 seconds
   - Zero manual rollbacks
   - No service interruptions

2. ✅ **All validations pass**
   - 10-point checklist: 10/10 checks pass
   - Within 2 hours of cutover
   - Zero test transaction failures

3. ✅ **Performance meets SLA**
   - Error rate <0.5% after 24 hours
   - API latency p99 <200ms
   - Uptime >99.5%

4. ✅ **Real customer success**
   - 5+ successful customer transactions
   - 3+ partner signups
   - $0 revenue loss

5. ✅ **All features operational**
   - PeopleDesk: Support tickets live
   - Partner Network: Affiliates can sign up
   - Rate Limiting: Active and working

6. ✅ **Monitoring & alerts live**
   - Real-time dashboards tracking
   - Auto-rollback configured
   - On-call team trained

7. ✅ **Communication complete**
   - Team debriefed
   - Customers notified
   - Status page updated

---

## Failure Scenarios & Recovery

### Scenario 1: Pre-Cutover Failure (Hour 0-6)

**If any Phase A check fails**:
1. Fix the issue
2. Re-run the failed check
3. Get approval before proceeding
4. Delay cutover by 24 hours if needed

**Example**: Load test shows 5% error rate
- Action: Debug the performance issue
- Fix: Optimize slow queries or disable feature flag
- Re-test: Run load test again
- Decision: If pass, proceed; if fail, delay launch

---

### Scenario 2: DNS Cutover Fails (Hour 8:05)

**If DNS atomic switch doesn't complete**:
1. Immediately revert DNS back to workers.dev
2. Investigate what went wrong
3. Wait 30 minutes before attempting again
4. Re-run Phase B from B.1

**Automatic action**: If DNS resolution fails for 30 sec, revert in 5 min

---

### Scenario 3: Error Rate Spike (Hour 8-14)

**If error rate >5% for 10 minutes**:
1. System auto-alerts team
2. On-call engineer investigates (5 min)
3. If unresolved, auto-rollback triggers at 10-min mark
4. DNS reverts to workers.dev
5. Post-mortem begins immediately

---

### Scenario 4: Payment Processing Fails (Hour 8-24)

**If Razorpay webhook 100% fails for 2 minutes**:
1. IMMEDIATE SMS alert to Founder + Payment team
2. IMMEDIATE DNS revert to workers.dev
3. Activate incident bridge
4. Fix payment configuration
5. Re-test before attempting cutover again

---

## Key Contacts During Go-Live

| Role | Name | Phone | SMS | Slack |
|------|------|-------|-----|-------|
| **Execution Lead** | Founder | [PHONE] | Yes | @founder |
| **Backend Engineer** | [NAME] | [PHONE] | Yes | @backend-eng |
| **DevOps Engineer** | [NAME] | [PHONE] | Yes | @devops-eng |
| **SRE/Monitoring** | [NAME] | [PHONE] | Yes | @sre-eng |
| **QA Lead** | [NAME] | [PHONE] | No | @qa-lead |
| **Customer Success** | [NAME] | [PHONE] | No | @cs-manager |
| **Marketing Manager** | [NAME] | [PHONE] | No | @marketing |
| **Cloudflare Support** | — | [SUPPORT_PHONE] | — | — |
| **Razorpay Support** | — | [SUPPORT_PHONE] | — | — |

---

## Resource Links

| Resource | URL | Frequency |
|----------|-----|-----------|
| **Primary Dashboard** | https://app.datadoghq.com/dashboard/phase3-golive | Refresh every 30 sec |
| **Status Page** | status.dhansetuhub.in | Update every hour (if issues) |
| **Incident Bridge** | [Auto-created per incident] | On-demand |
| **Slack Channel** | #phase3-golive | 24/7 during cutover |
| **Email Distribution** | phase3-team@dhansetuhub.in | Pre-cutover briefing |

---

## Documentation Checklist

Before starting go-live, verify you have:

- [ ] PHASE3_COMPRESSED_GOLIVE.md (read & understood)
- [ ] GOLIVE_CHECKLIST.md (printed or accessible)
- [ ] INCIDENT_RESPONSE_PLAYBOOK.md (team reviewed)
- [ ] COMMUNICATION_TEMPLATES.md (loaded in editor)
- [ ] MONITORING_DASHBOARD.md (dashboards open)
- [ ] PHASE3_GO_LIVE_MASTER_INDEX.md (this file, for reference)
- [ ] verify_domain_infrastructure.sh (ready to run)
- [ ] CONTACT_LIST.json (phone numbers verified)
- [ ] STATUS_PAGE_DRAFT.md (staged)
- [ ] All team members confirmed ready

---

## Approval Sign-Off

**Before go-live can begin**, these approvals are required:

- [ ] **Founder**: "Phase 3 is ready to deploy" (A.6 checkpoint)
- [ ] **Backend Lead**: "All code is tested and stable"
- [ ] **DevOps Lead**: "Infrastructure is ready, monitoring configured"
- [ ] **SRE**: "Auto-rollback procedures tested and verified"
- [ ] **QA Lead**: "Load test passed, no critical issues"

**All approvals needed by**: [SPECIFY DATE/TIME] UTC

---

## Success Metrics Dashboard (Final Scoreboard)

```
Phase 3 Go-Live Scoreboard
═════════════════════════════════════════════════════════

EXECUTION METRICS:
  DNS Downtime:                  [______ sec]  (target: <30s)
  Time to validation pass:       [______ min]  (target: <120m)
  Rollbacks triggered:           [______ ]     (target: 0)
  Manual interventions:          [______ ]     (target: 0)

PERFORMANCE METRICS:
  Error rate (24h):              [______ %]    (target: <0.5%)
  API latency p99:               [______ ms]   (target: <200ms)
  Uptime:                        [______ %]    (target: >99.5%)
  Payment success rate:          [______ %]    (target: >95%)

BUSINESS METRICS:
  Customer transactions:         [______ ]     (target: ≥5)
  Partner signups:               [______ ]     (target: ≥3)
  Revenue generated:            ₹[______ ]    (tracking)
  Customer satisfaction:         [______ /5]   (tracking)

OVERALL VERDICT:
  ✅ LIVE & OPERATIONAL
  ⚠️ LIVE WITH MINOR ISSUES
  ✗ ROLLED BACK (requires investigation)

Authorized by: _________________________ | Date: __________
```

---

## Post-Launch Checklist (After Hour 72)

**Owner**: Founder | **Deadline**: Hour 72

- [ ] 10-point validation checklist: ALL PASS
- [ ] 3 real customer transactions: SUCCESSFUL
- [ ] Partner network: Live with 3+ signups
- [ ] Error rate: Stable at <0.5% for 24 hours
- [ ] Monitoring: 24/7 tracking active
- [ ] Team: Debriefed and documented learnings
- [ ] Customers: Notified of new features
- [ ] Status page: Updated with Phase 3 features
- [ ] Support team: Trained on PeopleDesk
- [ ] Marketing: Launched partner recruitment campaign

**FINAL VERDICT**: Phase 3 is [LIVE / PARTIAL / ROLLED BACK]

---

## Questions Before Starting?

Review these sections:

- "What if something goes wrong?" → INCIDENT_RESPONSE_PLAYBOOK.md
- "What should I say to the team?" → COMMUNICATION_TEMPLATES.md
- "How do I know if we're healthy?" → MONITORING_DASHBOARD.md
- "What's the exact sequence?" → PHASE3_COMPRESSED_GOLIVE.md
- "How do I track progress?" → GOLIVE_CHECKLIST.md

---

**Document Version**: 1.0 | **Last Updated**: 2026-10-01 | **Status**: Ready for Founder Execution

**🚀 Phase 3 Compressed Go-Live Framework is COMPLETE and READY**

All documents are production-ready. Founder can begin execution immediately.
