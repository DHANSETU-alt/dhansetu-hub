# BlackBoxOps_OS Offer — Deliverables & Exclusions

Date: 2026-09-13
Status: **draft for founder review** — this is a reviewable doc, not
published to the live site. Pricing-page-adjacent copy is treated as
HIGH-risk in `docs/v3.4/HIGH_RISK_APPROVAL_RULES.md` (it directly shapes
what a paying customer expects) — it goes live only after you say so, and
only alongside a real production verification pass like every other
pricing change this session.

This exists because the readiness scorecard flagged a real gap: the
current pricing cards' "included" list is accurate, but there's no
explicit exclusions statement anywhere — only the refund policy implies
it indirectly. This doc is meant to be the source the actual page copy
gets drawn from, once you review it.

## What "lifetime access" actually buys today (real, verified)

**Live and working right now**, verified this session and prior sessions
via real signup/AI-generation calls:
- Business Planner — turns a raw idea into a one-page plan with a real
  first revenue target.
- Offer Generator — builds a named, priced, sellable offer with a real
  guarantee attached.

**Not live yet — roadmap, not built**, regardless of what the pricing
card's checklist implies about "every module":
- Lead Generator, CRM Workspace, Outreach Engine
- SOP Builder, Automation Studio, Revenue Dashboard, Pricing Advisor

The pricing card's own copy already says "on the roadmap" for these — this
section exists so that framing is repeated here explicitly, not softened.

## What lifetime access means in practice

- One payment, no subscription, no recurring charge — real, enforced
  server-side (Razorpay order amount is always server-computed, never
  client-supplied).
- Access to Business Planner and Offer Generator continues indefinitely
  from the day of payment.
- As the roadmap modules above actually ship, lifetime-access customers
  get them at no extra charge — this is a real, standing commitment, not
  a vague future promise, and should be treated as one: don't ship a new
  paid tier for existing modules without separately deciding how that
  interacts with existing lifetime customers.

## Exclusions — explicitly, what is NOT included

- No guarantee of any specific revenue outcome. The product helps
  structure a plan and an offer; it does not sell on the customer's
  behalf, run their outreach, or guarantee a sale.
- No dedicated onboarding call, custom implementation, or done-for-you
  service — this is self-serve software, not a consulting engagement.
- No SLA on response time beyond the real refund-policy commitment
  (7-day full refund if something is genuinely broken).
- No access to founder-side internal tooling (Shakthi_OS itself, the CEO/
  Sentinel/Security agent layer, or any of the founder's own business
  data) — customers get the BlackBoxOps_OS product surface only.
- No guaranteed timeline for roadmap modules. "On the roadmap" means
  real, planned work — not a committed ship date.

## Relationship to the existing refund policy

The real `/refund-policy` page already covers the "it doesn't work as
described" case (7-day full refund). This doc doesn't replace that — it
exists one layer up, defining what "as described" actually means, so a
future support conversation has a real, written reference instead of an
implicit understanding.

## Recommended next step

Fold a short version of the Exclusions section into the pricing card
itself (a single collapsible "What's not included" line, matching the
page's existing honest tone) once you've reviewed this draft — small
enough to ship as a LOW-risk copy change once the exclusions language
itself is approved.
