# blackboxOps_OS Migration Plan

Status: **staging built, nothing deployed, production untouched.** Full compliance with "Do NOT modify production immediately" / "DO NOT DEPLOY" / "DO NOT DELETE EXISTING SITE YET."

## What's still genuinely blocked

Asked twice (in the founder status report and again directly), still unanswered: **which local project — `dhansetu-hub-live`, `dhansetu-pdf-studio`, `dhansetu-peopledesk`, `partner-roadmap`, or `public-landing` — is actually deployed as blackboxops.co.in.** This plan proceeded anyway by decoupling what depends on that answer from what doesn't:

- **Phase 1 (backup)** didn't need it — backed up the live site directly over HTTP instead. See `WEBSITE_BACKUP_REPORT.md`.
- **Phases 2–5 (staging build)** didn't need it either — built as new pages reusing SHAKTHI OS's real, already-working backend, not a modification of whichever repo is live.
- **A real production cutover does need it** — you can't redeploy to a target you can't identify. That's the one thing still waiting. See `PRODUCTION_CUTOVER_PLAN.md`.

## What "blackboxOps_OS" actually is, now that it's been looked at

The live site (per the real backup) is **"BlackBoxOps AI — AI-assisted operations for small agencies,"** already running a working Razorpay checkout. The migration isn't inventing a product — it's re-platforming an existing one onto the multi-agent architecture already built and tested in SHAKTHI OS this session. That's a coherent story, not a guess.

## What was built (staging, local only, not deployed)

All under `dashboard/app/blackboxops-os/` in the same Next.js app SHAKTHI OS's own dashboard runs in — not a separate deployable project yet, because there's no known deploy target to build one for. Real, working, tested locally:

| Page | Real / Reused | Notes |
|---|---|---|
| Homepage | New copy, real branding | "Powered by GVC_INC" footer, honest "STAGING — not live" banner |
| Command Center | Reuses `/api/governor`, `/api/ceo/health`, `/api/incidents`, `/api/workers` | Same live data as the internal dashboard |
| Agent Visualization | **Literally the same `MissionControlFlow` component** as SHAKTHI OS's Mission Control, rebranded via a `brand` prop | Proves "single source of truth, no duplicate development" isn't just a slogan — verified with a screenshot |
| ERT Center | Reuses `/api/incidents` | Same real incident data |
| Pricing | Real Razorpay + PayU checkout calls (`orchestrator/pricing.py`, `payment_gateway_manager.py`) | Prices are **proposed, not confirmed** (₹2,999/mo Starter, ₹7,999/mo Growth) — placeholders for a working flow demo, not a launch decision |
| Customer Portal | **Not built** — flagged honestly on the page itself | Needs real user accounts (signup/login/sessions), which nothing in this project has; the existing `product_usage`/`product_subscriptions` tables key on email only, not enough for a real login-protected account page |

## Integration status (Phase 4)

- **Razorpay**: real, tested this session (`payments.py`, `payment_gateway_manager.py`), reused directly.
- **PayU**: real, hash-formula independently verified against a hand-built reference string (not just self-consistency), reused directly.
- **Neither has been tested against a live merchant account on this specific product** — same honesty standard as every other payment integration built this session. The Pricing page's checkout has a "Founder Test Mode" panel specifically so you can run that first real test yourself, without customer credentials ever touching a customer-facing form.

## Phase 5 — agents, reused not rebuilt

CEO, Sentinel, Security, Finance, Chrome Developer, Website Builder, Worker Pool, ERT are the **same real modules** already built and tested in SHAKTHI OS — the "n8n-style animated neon visualization" is the real `MissionControlFlow` React Flow + Framer Motion component, not a new implementation. This is what "single source of truth: GVC_OS Core, no duplicate development" means in practice, not just in the architecture diagram.

## What's next

1. Founder review of the staging pages (screenshots already captured; live at `/blackboxops-os` on this Mac).
2. Real blackboxOps_OS pricing decision (replacing the proposed ₹2,999/₹7,999 placeholders).
3. Real user-account system, scoped as its own piece of work, before Customer Portal can be real.
4. The folder-identity answer, before `PRODUCTION_CUTOVER_PLAN.md`'s steps can actually be executed rather than just planned.

See `LAUNCH_CHECKLIST.md` for the concrete go/no-go list and `PRODUCTION_CUTOVER_PLAN.md` for what happens once the target is known and approved.
