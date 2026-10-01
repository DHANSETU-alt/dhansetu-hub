# SHAKTHI_OS v5.1 — Decision Rules

Date: 2026-09-13
Builds on, does not replace: `docs/v3.4/HIGH_RISK_APPROVAL_RULES.md` (the
real gate mapping — `decisions` table Gate A, `bugs.status` Gate B, chat
confirmation Gate C). This document is the founder's v5.1 risk-tier
framing, cross-referenced to those real gates.

## 1. Risk tiers

### LOW — proceed automatically, no approval needed
UI copy, page layout, cards, CTAs, docs, local reports, non-destructive
bug fixes. This is most of what a session should do without asking.

### MEDIUM — proceed, but verify and log
Forms, routing, local data models, analytics tags, pricing *display*
(not the underlying charge amount/gateway), lead tracker changes. Always
followed by a real check: typecheck/build/test, or a query confirming
data landed where expected — never assumed.

### HIGH — stop and request founder approval before acting
Payment integration/charge logic, auth secrets/OAuth, DNS/domain changes,
production deploy, deleting data, bulk outreach/messaging, live email
deletion, firewall/security changes, any legal/financial guarantee.

Real example from today: the pricing-tier *redesign* (copy, tier
structure, server-side amount logic) was treated as MEDIUM-proceeding
work once the founder had given the direction ("one time not subscription
wise") — but the decision of *which exact amounts* (₹149/₹399) was flagged
back to the founder as unconfirmed rather than silently finalized, and the
actual *publish to production* was held for explicit confirmation (HIGH:
production deploy) before using the ChatGPT Sites builder to ship it.

## 2. The "ask less" checklist

Before asking the founder a question, check in order:
1. Can I infer the answer safely from the existing stated goal?
2. Is there a reversible default I can take instead?
3. Is there a low-risk implementation path that doesn't require the
   answer at all?
4. Can I continue with a placeholder/fallback and flag the assumption?
5. Can I document the assumption transparently and proceed?

Only ask when:
- A wrong decision could cost real money.
- A wrong decision could break auth, payment, domain, or security.
- Real legal/financial risk exists.
- User intent is genuinely ambiguous between materially different
  outcomes (not just phrasing).

Real example: when the founder said "we discuss new price range... you
have to wired," this session did NOT ask whether to proceed with pricing
copy at all (clearly in-scope, low-risk) — but did ask whether to
actually deploy live payment-pricing code via the ChatGPT Sites builder
vs. wait for git credentials, since that specific action (production
deploy of payment logic) sits squarely in the HIGH tier the founder
defined.

## 3. Mapping to the real existing gates (v3.4)

| This doc's tier | Real mechanism today |
|---|---|
| LOW | No gate — proceed. |
| MEDIUM | Verify via build/test/query; no approval row needed. |
| HIGH | Gate C (explicit chat confirmation) for direct session actions; Gate A (`decisions` table, `ceo.yaml`-scored) or Gate B (`bugs.status` ceo_approved/rejected) for agent-pipeline-dispatched work. |

No new approval mechanism was invented for v5.1 — see
`HIGH_RISK_APPROVAL_RULES.md` section 3 for why a single unified queue
across both mechanisms doesn't exist yet, and isn't fabricated here either.
