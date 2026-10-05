# BlackboxOps Free Trial & Freemium Tier Specification

**Document Version:** 1.0  
**Date:** 2026-10-05  
**Owner:** Product Team  
**Status:** Ready for Engineering  

---

## Executive Summary

This specification defines a dual-tier user acquisition funnel: a 7-day limited free trial (high-touch, upgrade-driven) and a permanent freemium tier (no card required, sustainable). Together, these remove friction for new users while maintaining clear upgrade paths to the ₹1,999 paid tier.

**Goal:** Remove signup friction → drive activation → convert via timely CTAs.

---

## 1. FREE TRIAL FLOW

### 1.1 User Segment & Eligibility
- **Target:** New users signing up via landing page or email invite
- **Eligibility:** Email verification only (no credit card required upfront)
- **Duration:** 7 calendar days from account creation
- **Auto-conversion:** On Day 8, user reverts to Freemium tier (if unpaid)

### 1.2 Trial Resource Limits (Hard Caps)

| Resource | Limit | Notes |
|----------|-------|-------|
| Active Workflows | 3 | Total concurrent, can delete & recreate |
| Agents | 2 | Total agents (reusable across workflows) |
| API Calls/day | 10,000 | Soft limit; warning at 80% |
| Storage | 100 MB | Logs + artifacts |
| Support | In-app chat only | No email support |

### 1.3 Trial Landing Flow

```
Landing Page (CTA: "Try Free for 7 Days")
         ↓
Email Signup Form
(Email, Password, Name)
         ↓
Email Verification Link
(Sent to inbox, valid 24h)
         ↓
Account Created + Onboarding Wizard
(Welcome screen, Day 1 email sent)
         ↓
Trial Dashboard
(3 empty workflow slots visible)
         ↓
First Workflow Template
(Pre-built: "Monitor Website Health" or "Email Summary Bot")
```

### 1.4 Email Copy & Timing

#### **Email 1: Welcome (Day 0 - sent immediately)**
```
Subject: Your 7-day BlackboxOps Trial is ready 🚀

Hi [NAME],

Your free trial is live. You have:
- 7 days (until [DATE at 11:59 PM IST])
- 3 active workflows
- 2 agents to build with

👉 Start your first workflow: [LINK to onboarding]

What you can do:
✓ Build autonomous agents
✓ Create multi-step workflows
✓ Integrate with 50+ platforms
✓ See live results

Questions? [In-app chat] is always open.

Happy building!
The BlackboxOps Team
```

#### **Email 2: Feature Unlock (Day 3)**
```
Subject: Unlock Integrations – Day 3 ✨

Hi [NAME],

You're crushing it! 👏 You've created [X] workflows in 3 days.

Here's what we just unlocked for you:
→ Telegram, Slack, Webhooks
→ Gmail, Google Sheets, Airtable
→ Stripe, Razorpay, custom API

[LINK: Integrations gallery]

These stay available through Day 7. Ready to build something bigger?

[BUTTON: Upgrade to Paid]

Cheers,
The BlackboxOps Team
```

#### **Email 3: Success Story (Day 5)**
```
Subject: See what other builders made in 5 days ⭐

Hi [NAME],

Inspired by your workflow progress, check out what one user built:

[TESTIMONIAL BLOCK]
"I automated my entire customer feedback loop in 4 days.
Now it saves me 10 hours/week." — Priya, SaaS Founder

[IMAGE: Screenshot of workflow]

Want similar results? Upgrade to unlock:
→ Unlimited workflows & agents
→ 24/7 priority email support
→ Advanced analytics & exports

[BUTTON: Upgrade to Paid – ₹1,999/month]

Still exploring? No pressure. You have 2 days left.

The BlackboxOps Team
```

#### **Email 4: Trial Ending Notice (Day 6)**
```
Subject: Your trial ends in 24 hours – Here's what you'll lose

Hi [NAME],

Tomorrow, your free trial ends. After that:
❌ Workflows will pause
❌ New workflow creation locked
❌ Agents will be archived

**But you can keep everything by upgrading.**

Upgrade now and get:
✓ Unlimited workflows & agents
✓ 3-year workflow history
✓ Email + chat support
✓ Advanced integrations

[BUTTON: Upgrade to Paid – ₹1,999/month]

Want to keep exploring for free? 
[LINK: Switch to Freemium tier (permanent, 5 workflows)]

Only valid until midnight tomorrow.

The BlackboxOps Team
```

#### **Email 5: Trial Expired (Day 8)**
```
Subject: Your trial has ended – Freemium tier activated ✅

Hi [NAME],

Your 7-day trial ended. Your account is now on our **free Freemium tier**.

What's active now:
✓ 5 workflows/month
✓ 3 agents
✓ Email support
✓ Community access

Your trial workflows were archived (not deleted—we can restore 1 for free).

Next step?
→ [LINK: Restore a workflow]
→ [LINK: Upgrade to Paid]
→ [LINK: Freemium tier details]

We'd love to have you stay. Let us know how we can help.

The BlackboxOps Team
```

---

## 2. FREEMIUM TIER (Permanent)

### 2.1 Freemium Positioning
- **Who:** Users choosing the free option (no trial, permanent)
- **Card Required:** No
- **Upgrade Path:** Single-click to ₹1,999/month tier
- **Sustainability:** Built for long-term free users + conversion funnel

### 2.2 Freemium Resource Limits

| Resource | Limit | Notes |
|----------|-------|-------|
| Active Workflows | 5 per calendar month | Resets monthly (1st of month) |
| Agents | 3 | Persistent, can reuse across workflows |
| API Calls/day | 5,000 | Soft limit; warning at 80% |
| Storage | 50 MB | Logs + artifacts (30-day retention) |
| Support | Email only | 48-hour response SLA |
| Integrations | 20 out of 50+ | Excludes: Premium APIs (Slack Team, Salesforce, Enterprise Zapier) |
| Workflow Runs/month | 1,000 | Total executions across all workflows |

### 2.3 Freemium Landing & Signup

```
Marketing Page: "Start Free"
         ↓
Choose Plan Page
[Free (Freemium)]  [Paid - ₹1,999/month]
         ↓
Simple Email Signup
(Email, Password, Name - no card modal)
         ↓
Email Verification
         ↓
Freemium Dashboard
(5 workflow slots, 3 agent slots visible)
         ↓
Suggested First Template
```

### 2.4 Freemium Dashboard UI Elements

- **Workflow Counter:** "2 of 5 workflows used this month"
  - Progress bar with "Upgrade" button when 80%+ used
- **Agent Counter:** "3 of 3 agents created"
  - "Delete unused agent" suggestion when at limit
- **API Usage Widget:** "1,234 of 5,000 API calls today"
  - Resets at midnight IST
- **Upgrade Sticky Banner:** (bottom of screen, dismissable)
  - Copy: "Unlimited workflows + agents + priority support"
  - CTA: "Upgrade to Paid – ₹1,999/month"

### 2.5 Upgrade CTA Placement (Freemium)

| Location | Copy | Trigger |
|----------|------|---------|
| Dashboard top-right | "Upgrade" | Always visible |
| Workflow creation modal | "Create another workflow?" + upgrade CTA | When user hits 5-workflow limit |
| Agent creation modal | "You've hit your agent limit" + upgrade details | When user hits 3-agent limit |
| Analytics page | "Unlimited data exports" (upgrade-only feature) | Always visible as disabled feature |
| Integrations gallery | "Premium integrations unlocked" | Hovering over locked integration tiles |

---

## 3. ONBOARDING SEQUENCE

### 3.1 Email + In-App Orchestration Timeline

| Trigger | Medium | Content | Timing |
|---------|--------|---------|--------|
| Email Verified | Email + In-app banner | Welcome message + first template offer | Immediate |
| Workflow Created | In-app tooltip | "Nice! Here's how to add your first agent" | Immediate |
| Day 3 (Trial only) | Email | Feature unlock (integrations gallery) | Day 3, 10 AM IST |
| Day 5 (Trial only) | Email | Success story + upgrade nudge | Day 5, 2 PM IST |
| Day 6 (Trial only) | Email | "Trial ending" urgent notice | Day 6, 9 AM IST |
| Day 8 (Trial→Freemium) | Email | "Welcome to Freemium tier" | Day 8, 8 AM IST |
| Monthly limit hit (Freemium) | In-app toast | "You've used X of 5 workflows this month" | When limit reached |
| 30 days on Freemium | Email | "30 days on BlackboxOps - here's what you built" + success story | Day 30 of Freemium |

### 3.2 In-App Onboarding Wizard (Day 0)

**Screen 1: Welcome**
```
Headline: "Welcome to BlackboxOps"
Subhead: "Build AI agents without code. In 3 minutes."

[Illustration: Agent icon + workflow)

[BUTTON: Let's Build]
```

**Screen 2: Choose Your First Template**
```
Headline: "What would you like to build?"

[Card 1] Website Monitor
Text: "Get alerts when your site goes down"
Tags: #monitoring #alerts
Difficulty: Beginner
[Choose button]

[Card 2] Email Summary Bot
Text: "Summarize emails into Slack daily"
Tags: #email #automation
Difficulty: Beginner
[Choose button]

[Card 3] Lead Qualification Agent
Text: "Auto-score inbound leads from your form"
Tags: #sales #leads
Difficulty: Intermediate
[Choose button]

[Skip button] "I'll build from scratch"
```

**Screen 3: Template Confirmation**
```
Headline: "Ready to create '[Template Name]'?"

Features this workflow includes:
✓ Scheduled trigger (daily)
✓ 2 agents (Analyzer + Emailer)
✓ Slack integration
✓ Smart retry on failure

[BUTTON: Create Workflow]
[Link: "Show me the details first"]
```

**Screen 4: Workflow Created ✓**
```
Headline: "Your first workflow is live!"

[Confetti animation]

What's next?
→ Test it now
→ Invite your team (Paid only)
→ Explore integrations
→ Watch 2-min video

[BUTTON: Go to Dashboard]
```

### 3.3 In-App Messaging Strategy

**Toast Notifications (appear bottom-right, auto-dismiss in 6s)**

```
After 1st workflow creation:
"🎉 Workflow created! It's running now."
[LINK: View results]

When Freemium user hits workflow limit:
"📊 You've used 5 of 5 workflows this month.
Create another? [Upgrade] [View current workflows]"

When API usage hits 80%:
"⚠️ You're at 80% of your daily API limit.
Upgrade for 3x more. [Learn more]"

When trial has 1 day left:
"⏰ Your trial expires in 24 hours.
[Upgrade now] [Keep free Freemium]"
```

**In-App Banner (persistent, but dismissable)**
```
Location: Top of dashboard
Visibility: Freemium users only
Duration: Persistent (reappears 7 days after dismiss)

Copy (rotating):
1. "Unlimited workflows. Priority support. ₹1,999/month."
   [Upgrade] [Maybe later]

2. "Upgrade to unlock advanced integrations."
   [See what's included] [Upgrade]

3. "Join 500+ teams using BlackboxOps Pro."
   [See their workflows] [Upgrade]
```

---

## 4. CONVERSION MECHANICS

### 4.1 Trial → Paid Conversion Flow

```
User clicks "Upgrade" button
         ↓
Pricing modal appears
(Trial user sees trial ending date prominently)
         ↓
Plan selection: ₹1,999/month (annual option: ₹19,999)
         ↓
Razorpay payment modal
(Phone + UPI, Card, Netbanking)
         ↓
Payment confirmed → Account upgraded
         ↓
Confirmation email + Welcome to Paid email
```

### 4.2 Freemium → Paid Conversion Flow

```
User clicks "Upgrade" button
         ↓
Pricing modal appears
(Freemium user sees benefits comparison)
         ↓
Plan selection: ₹1,999/month (annual option: ₹19,999)
         ↓
Razorpay payment modal
(Phone + UPI, Card, Netbanking)
         ↓
Payment confirmed → Account upgraded
         ↓
Confirmation email + "Welcome to Paid" email
         ↓
Archived workflows restored automatically
```

### 4.3 Upgrade Email (Confirmation)

```
Subject: Welcome to BlackboxOps Pro! 🎉

Hi [NAME],

Your upgrade is confirmed. You now have:
✓ Unlimited workflows & agents
✓ 3-year workflow history
✓ Priority email + chat support (4-hour SLA)
✓ Advanced analytics & data exports
✓ All 50+ integrations unlocked

Your workflows are live and running. No downtime.

[LINK: View your dashboard]
[LINK: Explore Pro features]

Have questions? Reply to this email anytime.

Welcome aboard!
The BlackboxOps Team
```

---

## 5. TECHNICAL IMPLEMENTATION SPECS

### 5.1 Database Schema Changes

**Table: `user_subscriptions`**
```sql
ALTER TABLE user_subscriptions ADD COLUMN (
  tier ENUM('trial', 'freemium', 'paid') DEFAULT 'trial',
  trial_start_date TIMESTAMP,
  trial_end_date TIMESTAMP,
  freemium_workflow_count INT DEFAULT 0,
  freemium_agent_count INT DEFAULT 3,
  last_workflow_reset_date DATE,
  monthly_api_calls INT DEFAULT 0,
  monthly_api_reset_date DATE
);
```

**Table: `onboarding_events` (new)**
```sql
CREATE TABLE onboarding_events (
  id UUID PRIMARY KEY,
  user_id UUID FOREIGN KEY,
  event_type VARCHAR(50), -- 'email_sent', 'cta_clicked', 'template_selected'
  event_data JSONB,
  created_at TIMESTAMP
);
```

### 5.2 Email Service Integration

**Provider:** SendGrid / Brevo (based on existing stack)

**Email Templates (IDs):**
- `welcome_trial` (Day 0)
- `feature_unlock_trial` (Day 3)
- `success_story_trial` (Day 5)
- `trial_ending_notice` (Day 6)
- `trial_expired_freemium` (Day 8)
- `upgrade_confirmation` (On payment)
- `freemium_30_day` (Day 30 of Freemium)

### 5.3 Cron Jobs Required

```yaml
Daily (midnight IST):
  - Reset API call counters
  - Check for trial expirations (Day 8)
  - Send day-specific trial emails

Monthly (1st of month, 12 AM IST):
  - Reset Freemium workflow counters
  - Check for Freemium → overdue users
  - Archive workflows over limit

Hourly:
  - Check API usage (warn at 80%)
  - Update user tier status
```

### 5.4 Feature Flags

```yaml
feature_trial_enabled: true
feature_freemium_enabled: true
trial_days: 7
freemium_workflows_per_month: 5
freemium_agents_per_account: 3
upgrade_prompt_frequency: 'daily'
```

### 5.5 Analytics Events to Track

```
Funnel metrics:
- signup_landing_page
- email_verified
- trial_accepted / freemium_selected
- first_workflow_created
- cta_clicked (which CTA, when)
- payment_initiated
- payment_completed
- trial_expired
- upgraded_to_paid
- payment_failed

Engagement metrics:
- days_until_first_workflow
- workflow_runs_per_trial_user
- api_calls_per_tier
- emails_opened_rate (by template)
- cta_click_rate (by placement)
```

---

## 6. COPY STYLE GUIDE

### 6.1 Tone & Voice
- **Friendly, not corporate:** Use "Hi" instead of "Dear", contractions, casual punctuation
- **Action-oriented:** Lead with benefit, then CTA
- **Urgency without pressure:** "Tomorrow" not "NOW", "You have X days" not "DON'T MISS OUT"
- **Personal:** Use [NAME], reference user's actions ("You created 2 workflows!")

### 6.2 CTA Button Copy
- **Upgrade buttons:** "Upgrade to Paid – ₹1,999/month"
- **Trial-specific:** "Upgrade Now (2 days left)"
- **Freemium-specific:** "Upgrade – Unlock Unlimited"
- **Avoid:** "Click here", "Submit", "Proceed"

### 6.3 Price Framing
- Always show: **₹1,999/month** or **₹19,999/year** (annual shows 17% savings)
- Freemium tier: "Free forever" (reassurance)
- Trial tier: "Free for 7 days, then Freemium"

---

## 7. PAID TIER POSITIONING

### 7.1 Feature Comparison Matrix

| Feature | Trial (7d) | Freemium | Paid |
|---------|-----------|----------|------|
| Active Workflows | 3 | 5/month | Unlimited |
| Agents | 2 | 3 | Unlimited |
| API Calls/day | 10K | 5K | 50K |
| Storage | 100 MB | 50 MB | 10 GB |
| Integrations | 20 | 20 | All 50+ |
| Support | In-app chat | Email (48h) | Email + chat (4h) |
| Workflow History | 7 days | 30 days | 3 years |
| Team Members | Not allowed | Not allowed | Up to 5 |
| Custom Integrations | ❌ | ❌ | ✓ |
| SLA | None | None | 99.5% uptime |
| Price | Free | Free | ₹1,999/mo |

---

## 8. ROLLOUT PLAN

### Phase 1: Infrastructure (Week 1)
- [ ] Database schema updates
- [ ] Email template setup (SendGrid)
- [ ] Cron job configuration
- [ ] Analytics event tracking

### Phase 2: Trial Flow (Week 1-2)
- [ ] Landing page → trial signup
- [ ] Email automation (all 5 trial emails)
- [ ] Trial dashboard UI (workflow counter, limit warnings)
- [ ] Day 8 auto-conversion (trial → freemium)

### Phase 3: Freemium Tier (Week 2)
- [ ] Freemium signup flow
- [ ] Freemium dashboard UI
- [ ] Monthly reset logic
- [ ] Upgrade CTAs (all placements)

### Phase 4: Testing & QA (Week 2-3)
- [ ] End-to-end trial flow (all 7 days)
- [ ] Email delivery + link tracking
- [ ] Payment flow (Razorpay integration)
- [ ] Tier limits enforcement (workflow, API, storage)

### Phase 5: Launch (Week 3)
- [ ] Feature flag rollout (10% → 50% → 100%)
- [ ] Monitor conversion funnel
- [ ] Customer support readiness
- [ ] Marketing coordination

---

## 9. SUCCESS METRICS

### 9.1 Primary Metrics (Track Weekly)

| Metric | Target | Notes |
|--------|--------|-------|
| Trial signup rate | 15% of landing visitors | Baseline: measure at launch |
| Trial → Freemium conversion (Day 8) | 70% of trial users stay | Auto-conversion, high expected |
| Trial → Paid conversion | 8-12% of trial users | 7-day window |
| Freemium → Paid conversion | 2-4% per month | Slower, but sustainable |
| Freemium churn (monthly) | <15% | Users who stop logging in |
| Email open rate | 35%+ | All trial emails |
| CTA click rate | 12%+ | "Upgrade" buttons |

### 9.2 Cohort Analysis
- **Cohort A:** Trial signup → Paid by Day 7
- **Cohort B:** Trial → Freemium, Paid within 30 days
- **Cohort C:** Freemium only (no paid conversion) — study churn triggers

### 9.3 Feedback Loops
- **Post-signup survey:** "What brought you here?" (top 5 use cases)
- **Trial day 3 check-in:** "Need help with anything?" (identify blockers)
- **Post-trial:** "Why not upgrade?" (collect objections)
- **Monthly Freemium check-in:** "What would make you upgrade?" (feature requests)

---

## 10. APPENDIX: Exact Email Templates

All email templates use the following footer:

```
---
BlackboxOps | Autonomous Workflows for Everyone
[unsubscribe link] | [manage preferences] | [help center]

© 2026 BlackboxOps. All rights reserved.
support@blackboxops.co.in
```

---

## Handoff Checklist for Engineering

- [ ] Product manager confirms spec is complete
- [ ] Designer has mockups for trial & freemium dashboards
- [ ] Backend engineer confirms database schema plan
- [ ] Email engineer has all 5+ email templates
- [ ] QA has test cases for all flows
- [ ] DevOps has cron job runbooks
- [ ] Analytics has event tracking spec
- [ ] Customer support trained on tier differences
- [ ] Marketing has launch timeline & messaging
- [ ] CEO approval on pricing & CTA copy

---

**Next Step:** Engineering lead → Jira ticket creation (1 epic, 3 stories minimum)
