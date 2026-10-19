# Phase 3 Communication Templates
**Pre-Written Notifications for Rapid Deployment**

---

## Instructions

Copy-paste ready templates for:
- **Team communications** (Slack, standup)
- **Customer notifications** (email, dashboard)
- **Partner notifications** (email, in-app)
- **Status page updates** (public, timestamped)

**Customization**: Replace `[BRACKETED FIELDS]` with real data before sending.

---

# TEAM COMMUNICATIONS

## Template 1: Pre-Cutover Team Standup (Hour 0)

**Channel**: #phase3-golive (Slack)  
**Timing**: 30 min before cutover starts  
**Owner**: Founder

```
🚀 PHASE 3 GO-LIVE COMMENCING IN 30 MINUTES

Team, we're kicking off the compressed Phase 3 cutover in 30 minutes.
Domain migration: dhansetuhub.workers.dev → dhansetuhub.in

📋 READINESS STATUS:
✅ All 481 tests passing
✅ Database backup verified
✅ SSL certificate valid
✅ Razorpay webhook configured
✅ Google OAuth URLs updated
✅ Monitoring dashboards live
✅ Load test results: 0.1% error rate

⏰ TIMELINE:
• Hour 0-6: Pre-cutover preparations
• Hour 6-12: DNS cutover & feature flag activation (CRITICAL WINDOW)
• Hour 12-24: Validation & real customer tests
• Hour 24-48: Full launch (marketing, outreach)
• Hour 48-72: Monitoring & debrief

🎯 SUCCESS CRITERIA:
✓ <30 sec DNS downtime
✓ Error rate <0.5% after 24h
✓ 5+ customer transactions processed
✓ 3+ partner signups
✓ All validations passing

⚠️ IF ANYTHING GOES WRONG:
• Error rate >5%? → Auto-rollback in 10 min
• Database connection fails? → Auto-rollback in 5 min
• Payment processing fails? → Immediate rollback
• See INCIDENT_RESPONSE_PLAYBOOK.md for details

📱 DURING CUTOVER (6-12 hours):
• Slack updates every 30 min
• All eyes on dashboards
• On-call team on standby
• No merges to main branch

🔗 Resources:
• Execution plan: PHASE3_COMPRESSED_GOLIVE.md
• Real-time tracker: GOLIVE_CHECKLIST.md
• Dashboards: https://app.datadoghq.com/dashboard/phase3
• Bridge: [Google Meet URL]

Everyone ready? React with ✅ when your system is prepped.
```

---

## Template 2: Cutover Window Update (Every 30 min, Hour 6-12)

**Channel**: #phase3-golive (Slack)  
**Timing**: Every 30 minutes during Hour 6-12  
**Owner**: SRE / Monitoring

```
📊 CUTOVER STATUS UPDATE [TIMESTAMP UTC]

⏱️ ELAPSED: [X hours Y minutes]
🎯 PHASE: [B.1 DNS TTL / B.2 Feature Flags / B.3 Rate Limiting / B.4 ATOMIC SWITCH / etc.]

CURRENT METRICS:
• Error rate: [X]% (target: <0.5%)
• API latency (p99): [X]ms (target: <200ms)
• Uptime: [X]% (target: 100%)
• Transactions: [X] successfully processed
• Rate-limited requests: [X]%

COMPLETED TASKS:
✅ [Task 1]
✅ [Task 2]
✅ [Task 3]

🔄 IN PROGRESS:
⏳ [Current task]
⏳ [Next task]

⚠️ ALERTS:
[If any: describe alert, action being taken, ETA to resolution]
[If none: "✅ All clear - no alerts"]

🟢 SYSTEM STATUS: [NOMINAL / DEGRADED / CRITICAL]

NEXT MILESTONE: [X] in [Y] minutes
Bridge: [Google Meet URL]
Questions? Reply in thread.
```

---

## Template 3: Successful Cutover Announcement (Hour 8:05)

**Channel**: #phase3-golive (Slack)  
**Timing**: Immediately after DNS atomic switch completes  
**Owner**: Founder

```
🎉 ATOMIC CUTOVER COMPLETE!

Domain: dhansetuhub.workers.dev → dhansetuhub.in ✅

📊 CUTOVER METRICS:
• Downtime: [X] seconds (target: <30 sec) ✓
• DNS propagation: Completed at [TIME] UTC
• First requests to new domain: [TIME] UTC
• API response time: [X]ms
• Error rate: [X]%

🟢 SYSTEM STATUS: OPERATIONAL
All services live on dhansetuhub.in

IMMEDIATE NEXT STEPS:
1. Start 10-point validation checklist
2. Monitor metrics closely
3. Run 3 test transactions
4. Update status page

⏰ VALIDATION PHASE: Next 2 hours (CRITICAL)
All team eyes on dashboards. Post updates every 30 min.

If you see any anomalies, report immediately in this thread.

🚀 Phase 3 is live!
```

---

## Template 4: Validation Phase - 10-Point Checklist Results (Hour 14)

**Channel**: #phase3-golive (Slack)  
**Timing**: After 10-point checklist completes  
**Owner**: QA Engineer

```
✅ PHASE 3 VALIDATION CHECKLIST - COMPLETE

10-Point Checklist Results:
✅ 1. Homepage loads correctly
✅ 2. API response time <200ms
✅ 3. Database connectivity OK
✅ 4. PeopleDesk module live
✅ 5. Partner Network module live
✅ 6. OAuth working
✅ 7. Razorpay webhook responding
✅ 8. Rate limiting active
✅ 9. Error rate <0.5%
✅ 10. SSL certificate valid

🟢 VALIDATION PASSED (10/10 checks)

Real-World Transactions Tested:
✅ New customer signup + ₹149 payment
✅ Existing customer upgrade to ₹399
✅ Partner signup + commission calculation

All transactions completed successfully.

🎯 VERDICT: PHASE 3 READY FOR FULL LAUNCH

Moving to Phase D:
• Marketing landing page activation
• Email campaign launch
• Social media announcements
• Customer outreach sequence

Next checkpoint: Hour 24 (Launch Phase)
```

---

## Template 5: Issue Detected - Auto-Rollback Triggered (Hour X)

**Channel**: #phase3-golive + SMS  
**Timing**: Immediately upon rollback trigger  
**Owner**: Automated system + Founder confirmation

```
🔴 CRITICAL INCIDENT - AUTO-ROLLBACK TRIGGERED

Reason: [Error rate exceeded 5% / Database connection failed / OAuth failure / etc.]

Detected at: [TIMESTAMP] UTC
Rollback initiated: [TIMESTAMP] UTC
Rollback completed: [TIMESTAMP] UTC

CURRENT STATUS:
✅ DNS reverted to dhansetuhub.workers.dev
✅ All services operational on backup
✅ Error rate normalized
✅ Customers unaffected (request routed to stable system)

IMPACT:
• Downtime: [X] minutes
• Users affected: [X]
• Revenue impact: ₹[X]

NEXT STEPS:
1. Incident investigation begins immediately
2. Emergency bridge in 5 minutes: [Google Meet URL]
3. Post-mortem scheduled for [TIME]
4. Fix + re-test before next attempt

STATUS PAGE UPDATED: Yes
CUSTOMER NOTIFICATION SENT: Yes
INCIDENT LOGGED: Yes

👀 All eyes on incident bridge now.
```

---

## Template 6: Successful Resolution - Ready to Re-Attempt (Hour X+2)

**Channel**: #phase3-golive (Slack)  
**Timing**: After root cause fixed and tested  
**Owner**: Founder + Technical Lead

```
✅ INCIDENT RESOLVED - ROOT CAUSE IDENTIFIED & FIXED

Issue: [Description of what went wrong]
Root Cause: [Detailed technical explanation]
Fix Applied: [What was changed/fixed]

🔬 TESTING RESULTS:
✅ Fix validated in staging
✅ Load test: 0% error rate on fix
✅ All unit tests passing
✅ Integration tests passing

🟢 READY FOR RE-DEPLOYMENT

Planning to re-attempt Phase 3 cutover in [X] minutes.

Changes from first attempt:
• [Change 1 - what we learned]
• [Change 2 - improvement]
• [Change 3 - additional safeguard]

Everyone refreshed? Let's go again. ✅ if ready.

Post-mortem: [TIME] for full debrief.
```

---

# CUSTOMER COMMUNICATIONS

## Template 7: Pre-Launch Announcement (Hour 0)

**Channel**: Email to all active customers  
**Timing**: 24 hours before cutover (or when ready)  
**Owner**: Marketing Manager

```
Subject: Exciting Update: New Features Coming to DhanSetu Hub 🚀

Hi [CUSTOMER_NAME],

We're thrilled to announce Phase 3 of DhanSetu Hub is launching this week 
with three powerful new capabilities:

🎟️ PEOPLEDESK - Built-in Support Tickets
   Create, track, and resolve support tickets directly in your dashboard.
   No more lost emails or communication gaps.

👥 PARTNER NETWORK - Earn Commissions
   Bring partners into your network and earn recurring commissions on 
   every transaction they generate. Scale your business faster.

⚡ RATE LIMITING - Account Protection
   Automatic rate limiting protects your account from abuse and ensures 
   fair resource allocation across all users.

📅 LAUNCH DATE: [DATE] UTC
🔗 STATUS PAGE: status.dhansetuhub.in (for real-time updates)

No action needed from you. Services will migrate to our new infrastructure 
on [DATE]. You'll see improved performance and new features available 
immediately in your dashboard.

Questions? Reach out to our new support team at support@dhansetuhub.in

Excited to bring you these improvements!

The DhanSetu Hub Team
```

---

## Template 8: During-Cutover Status Update (If Issues)

**Channel**: Email + dashboard banner  
**Timing**: If cutover takes longer than expected or issues arise  
**Owner**: Founder

```
Subject: DhanSetu Hub Maintenance Update [TIMESTAMP]

We're in the middle of upgrading our infrastructure to bring you new features.

🔧 CURRENT STATUS: [NOMINAL / INVESTIGATING / DEGRADED]

Timeline:
• Started: [TIME] UTC
• Expected completion: [TIME] UTC
• Current time: [CURRENT TIME] UTC

What's Happening:
We're migrating to our next-generation platform with:
• PeopleDesk (built-in support)
• Partner Network (affiliate commissions)
• Advanced rate limiting

✅ WHAT'S WORKING:
• [Service 1] - Full service available
• [Service 2] - Full service available

⏳ WHAT'S IN PROGRESS:
• [Feature 1] - Currently being activated
• [Feature 2] - Currently being tested

We'll send another update in 30 minutes.

Thank you for your patience!

Questions: support@dhansetuhub.in
Status: status.dhansetuhub.in
```

---

## Template 9: Launch Success Announcement (Hour 24)

**Channel**: Email to all customers  
**Timing**: After Phase C validation completes  
**Owner**: Founder + Marketing

```
Subject: 🎉 Phase 3 is Live! New Features Available Now

Hi [CUSTOMER_NAME],

We're delighted to announce that Phase 3 of DhanSetu Hub has officially 
launched with zero downtime!

✅ NEW FEATURES LIVE:

🎟️ PeopleDesk - Support Ticket System
   Your customers can now submit support tickets directly from your dashboard.
   Track, comment, and resolve issues all in one place.
   → Try it: [LINK_TO_PEOPLEDESK]

👥 Partner Network - Affiliate Program
   Sign up partners, track their commissions, and grow your business faster.
   Automatic commission calculations and payouts.
   → Invite partners: [LINK_TO_PARTNER_NETWORK]

⚡ Rate Limiting - Built-in Protection
   Your account is now protected with intelligent rate limiting.
   Prevents abuse while ensuring fair access for all users.
   → Learn more: [HELP_ARTICLE]

🚀 PERFORMANCE IMPROVEMENTS:
• 45% faster API response times
• 99.95% uptime guarantee
• Enhanced security with TLS 1.3

📊 USAGE THIS WEEK:
• [X] new support tickets created
• [X] partners signed up
• [X] transactions processed

🙏 THANK YOU for being part of Phase 3. Your feedback has shaped 
these features.

Ready to dive in? Log in to your dashboard now.

Questions? Our new support team is ready: support@dhansetuhub.in

Cheers,
The DhanSetu Hub Team
```

---

## Template 10: Incident Communication - Service Disruption (If Rollback)

**Channel**: Email to all customers  
**Timing**: If rollback occurs (immediately)  
**Owner**: Founder + Legal

```
Subject: DhanSetu Hub Service Update - [TIMESTAMP] UTC

We're aware of a service issue affecting DhanSetu Hub starting at [TIMESTAMP].

🔧 WHAT HAPPENED:
During a planned infrastructure upgrade, we encountered an issue that 
required us to revert to our backup systems to ensure stability.

🟢 CURRENT STATUS:
✅ Services are operational on our backup infrastructure
✅ All your data is safe and accessible
✅ No payment processing failures
✅ No data loss

⏰ INVESTIGATION:
Our engineering team is investigating the root cause. We expect to have 
more information within 1 hour.

📱 UPDATES:
Follow real-time updates at: status.dhansetuhub.in
Or check this email for updates.

🛠️ WHAT WE'RE DOING:
1. Root cause analysis (in progress)
2. Implementing fixes (planned)
3. Extensive testing (before re-deployment)
4. Re-deployment attempt (scheduled for [TIME])

💬 SUPPORT:
If you have urgent questions, reach out to support@dhansetuhub.in

WE APOLOGIZE for any inconvenience. We take your trust seriously and 
will have this fully resolved shortly.

Thank you for your patience and continued use of DhanSetu Hub.

The DhanSetu Hub Team
```

---

## Template 11: Post-Incident Resolution (After Fix & Re-Deployment)

**Channel**: Email to all customers  
**Timing**: After successful re-deployment  
**Owner**: Founder

```
Subject: ✅ DhanSetu Hub Fully Restored - Phase 3 Live!

Hi [CUSTOMER_NAME],

Great news! DhanSetu Hub is now fully operational with Phase 3 live.

✅ STATUS: FULLY OPERATIONAL

What Happened:
During yesterday's infrastructure upgrade, we encountered an issue that 
required us to revert to our backup systems. Our team quickly identified 
the root cause, implemented a fix, and re-deployed successfully.

🔍 ROOT CAUSE: [BRIEF, NON-TECHNICAL EXPLANATION]

🛠️ SOLUTION: [BRIEF EXPLANATION OF FIX]

🟢 PHASE 3 FEATURES NOW LIVE:
✅ PeopleDesk (support tickets)
✅ Partner Network (affiliate program)
✅ Advanced Rate Limiting

📊 IMPACT SUMMARY:
• Downtime: [X] hours
• Transactions affected: [X] (none lost)
• Data integrity: 100% verified
• User accounts: All secure

🚀 IMPROVEMENTS MADE:
To prevent this from happening again, we've:
• [Improvement 1]
• [Improvement 2]
• [Improvement 3]

💙 THANK YOU for your patience and understanding. Your trust in DhanSetu 
Hub means everything to us.

Questions? support@dhansetuhub.in

Onward!
The DhanSetu Hub Team
```

---

# PARTNER COMMUNICATIONS

## Template 12: Partner Launch Announcement

**Channel**: Email to partners  
**Timing**: At Hour 24 (launch)  
**Owner**: Partnership Manager

```
Subject: 🎉 Partner Network is Live! Start Earning Commissions Today

Hi [PARTNER_NAME],

Exciting news! The DhanSetu Hub Partner Network is now live, and you can 
start earning commissions immediately.

💰 HERE'S HOW IT WORKS:

1. Share your unique partner link: [PARTNER_LINK]
2. When customers sign up using your link, you earn a commission
3. Commissions are calculated automatically and paid monthly

📊 COMMISSION STRUCTURE:
• Basic plan (₹149/month): 25% recurring commission
• Premium plan (₹399/month): 30% recurring commission
• Enterprise plan: Custom negotiated rates

🚀 GET STARTED:
1. Log in to your partner dashboard: [LINK]
2. Grab your unique referral link
3. Share with your network (email, social, website)
4. Watch your commissions grow

📈 TOP PARTNERS THIS MONTH:
[PARTNER_1]: ₹[AMOUNT]
[PARTNER_2]: ₹[AMOUNT]
[PARTNER_3]: ₹[AMOUNT]

💬 SUPPORT:
Questions about commissions? Reach out: [PARTNER_SUPPORT_EMAIL]

Welcome to the Partner Network!

The DhanSetu Hub Growth Team
```

---

# STATUS PAGE UPDATES

## Template 13: Scheduled Maintenance Notice (24h before)

**Channel**: status.dhansetuhub.in  
**Timing**: 24 hours before cutover  
**Owner**: DevOps / Status Page Manager

```
🔧 SCHEDULED MAINTENANCE

Date & Time: [DATE] [TIME] UTC
Duration: Expected 6-12 hours
Impact: Infrastructure upgrade (all features may be temporarily unavailable)

What's Happening:
We're upgrading to Phase 3 infrastructure with new capabilities:
• PeopleDesk (support tickets)
• Partner Network (affiliate program)
• Advanced rate limiting

Service Impact:
🟡 PREDICTED: Services may be intermittently unavailable during the 6-hour 
   upgrade window. We're targeting <30 seconds of total downtime.

Real-time Updates:
Follow this page for live updates every 30 minutes during maintenance.

Questions: support@dhansetuhub.in
```

---

## Template 14: Maintenance In Progress

**Channel**: status.dhansetuhub.in  
**Timing**: Every 30 min during Hour 6-12  
**Owner**: SRE

```
🔧 MAINTENANCE IN PROGRESS

Started: [TIME] UTC
Expected completion: [TIME] UTC
Elapsed: [X] hours [Y] minutes

Current Phase: [DESCRIPTION OF CURRENT WORK]

Status: 🟡 MAINTENANCE
✅ Systems operational on backup
⏳ Upgrade in progress
📊 Metrics: [Current health summary]

Next update: [TIME] UTC
```

---

## Template 15: Maintenance Complete

**Channel**: status.dhansetuhub.in  
**Timing**: After Phase C validation completes  
**Owner**: DevOps

```
✅ MAINTENANCE COMPLETE

Status: 🟢 OPERATIONAL

Phase 3 is now live! New features available:
✅ PeopleDesk
✅ Partner Network
✅ Rate Limiting

Total downtime: [X] seconds

Performance:
• API latency: [X]ms
• Error rate: [X]%
• Uptime: [X]%

All systems healthy. Thank you for your patience!

Subscribe to updates: [RSS/Email Link]
```

---

# INTERNAL ESCALATION TEMPLATES

## Template 16: Escalation to Founder (Critical Issue)

**Channel**: SMS + Slack (direct message)  
**Timing**: If critical condition detected  
**Owner**: Automated system

```
🚨 CRITICAL INCIDENT - FOUNDER ACTION REQUIRED

Trigger: [Error rate >5% / Database failure / Payment processing failure]

Time: [TIMESTAMP] UTC
Duration: [X] minutes
Current status: [System state]

Auto-rollback scheduled for: [TIME] if not manually overridden

Options:
A) Let auto-rollback proceed (no action needed)
B) Override rollback and attempt manual fix (reply "OVERRIDE")
C) Escalate to infrastructure team (reply "ESCALATE")

Dashboard: [DATADOG_LINK]
Bridge: [GOOGLE_MEET_LINK]

Reply ASAP.
```

---

## Template 17: Executive Summary (Post-Incident)

**Channel**: Email to C-suite  
**Timing**: Day after incident (if one occurred)  
**Owner**: Founder

```
Subject: Phase 3 Go-Live Summary - [OUTCOME: SUCCESS / PARTIAL / ROLLBACK]

EXECUTIVE SUMMARY

Phase 3 infrastructure upgrade completed on [DATE] with [OUTCOME].

KEY METRICS:
• Scheduled downtime: <30 sec ✓
• Actual downtime: [X] seconds
• Error rate: [X]%
• Transaction success rate: [X]%
• Customer impact: [None / Minimal / Moderate]

PHASE 3 FEATURES NOW LIVE:
✅ PeopleDesk (support ticket system)
✅ Partner Network (affiliate commissions)
✅ Rate Limiting (DDoS/abuse protection)

BUSINESS IMPACT:
• New capacity: [X]% increase
• Performance improvement: [X]%
• Partner network activation: Ready
• Revenue opportunity: ₹[X] potential monthly

LESSONS LEARNED:
[If incident occurred]
• Issue: [What went wrong]
• Root cause: [Why]
• Fix: [Solution]
• Prevention: [What we're doing differently]

NEXT STEPS:
1. Full customer communication (sent)
2. Post-mortem debrief (scheduled)
3. Monitoring for 30 days
4. Full public announcement

Questions? Call [TIME]
```

---

## Approval Checklist Before Sending

Before sending ANY communication:

- [ ] All bracketed fields [FILLED_IN]
- [ ] Timestamps are in UTC and current
- [ ] Tone is professional but warm
- [ ] No technical jargon for customer communications
- [ ] Links are verified (not broken)
- [ ] Facts are verified (metrics, times, numbers)
- [ ] Spell-check passed
- [ ] Manager/Founder approved
- [ ] Distribution list is correct (don't send to wrong group!)

---

**Document Version**: 1.0 | **Last Updated**: 2026-10-01 | **Status**: Ready for Deployment
