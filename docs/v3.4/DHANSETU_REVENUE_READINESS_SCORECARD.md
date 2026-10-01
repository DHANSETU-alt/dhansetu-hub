# DhanSetu Revenue Readiness Scorecard — v3.4

Date: 2026-09-13
Scope: the active revenue engine is **blackboxops.co.in** (BlackBoxOps_OS),
per the standing gradual-rebrand direction — new revenue work targets
BlackBoxOps, not dhansetuhub.in directly. Where a category is genuinely
about the underlying SHAKTHI_OS internal system (e.g. lead storage,
automation reliability) rather than the customer-facing site, that's
called out per row.

Scoring rule (as specified): 0 = not started, 25 = planned only, 50 =
implemented but not verified, 75 = verified locally, 100 = verified live/
production with real evidence. **No row below is 100 without a cited,
checkable piece of evidence from this or a prior session.**

| # | Category | Score | Status | Evidence | Blockers | Next task | Agent |
|---|---|---|---|---|---|---|---|
| 1 | Website Professionalism | 100 | Verified live | Real screenshot + curl of blackboxops.co.in, 2026-09-13, this session; true-copy transcription of founder-approved artifact, footer run-together bug fixed | None current | Reconcile any remaining artifact-vs-real content drift as it's found | Website Implement Maker (`website_builder.yaml`) |
| 2 | Product Range | 50 | Implemented, partial | Business Planner + Offer Generator verified live with real signup/AI-gen calls (prior session); 8 other listed modules ("Lead Generator," "SOP Builder," etc.) are roadmap copy only, not built | 8/10 advertised modules don't exist yet | Pick the next single module to actually build, not add more roadmap copy | Website Implement Maker |
| 3 | Offer Stack | 75 | Verified live, docs gap | Real 3-tier ladder (Early Adopter ₹999 / Growth ₹2,999 / Pro ₹4,999) verified via production curl + screenshot, 2026-09-13 | Guarantee/exclusions language exists only implicitly in UI copy, not as a written policy | Write an explicit deliverables/exclusions one-pager | Strategy Maker (new agent, §2 of the plan) |
| 4 | Lead Capture | 50 | Implemented, not verified live on-site | Real `leads`/`lead_events` tables + `insert_lead()` in `orchestrator/db.py`, but no confirmed wiring from blackboxops.co.in visitor actions (SupportWidget) into this table — the DB and the live site are two different systems (D1 vs SQLite) | No confirmed on-site-to-CRM pipeline | Confirm/build the real bridge, or build the On-Site Bot Agent with its own storage | On-Site Bot Agent (new agent, §2 of the plan) |
| 5 | Pricing/Payment Readiness | 100 | Verified live | Real Razorpay checkout, real server-computed tier pricing, verified end-to-end via production curl + Chrome screenshot, 2026-09-13, this session | None current | Monitor real `payments` table for the first non-owner `status='paid'` row | Money Calculator (`finance.yaml`) |
| 6 | Trust/Legal Pages | 100 | Verified live | `/privacy`, `/terms`, `/refund-policy` real, live pages, referenced and edited across this session | None current | Update `/privacy`'s "no Google Analytics" claim the moment GA is actually turned on | Website Implement Maker |
| 7 | SEO/AI Visibility | 100 | Verified live | Google Search Console: `blackboxops.co.in` verified Domain property; real `sitemap.xml` + `robots.txt` live; sitemap manually submitted 2026-09-13 with founder's go-ahead — real screenshot shows "Sitemap submitted successfully," status Success, 5 pages discovered | None current | Monitor real indexing/impressions as they appear | Website Implement Maker |
| 8 | Analytics/Tracking | 100 | Verified live | Real GA4 property "BlackBoxOps_OS" created 2026-09-13 (G-P2HDNXZ5RP), wired into `layout.tsx`, real CSP `connect-src` bug found and fixed (google-analytics.com was missing, silently blocking every beacon), verified via real GA4 Realtime report showing "1 active user" from a live test visit; `/privacy` page's tracker disclosure updated in the same change | None current | Watch real traffic/conversion data as outreach begins | Website Implement Maker |
| 9 | Subscriber Acquisition | 50 | Implemented, unverified | Real outreach templates drafted (warm DM, public post, cold email) against the real live offer; one real send confirmed (WhatsApp to a named contact, prior session, read receipts confirmed) | No real payment has resulted yet; verified revenue is ₹0 | Send template 1 to the next named contact | Sales/Outreach (existing SHAKTHI_OS sales agents) |
| 10 | Automation Reliability | 50 | Implemented, not fully supervised | Real cron trigger (`*/5 * * * *`) confirmed on the `blackboxops-os` worker; but per `docs/v3.3/PHASE0_AUDIT.md`, the core orchestrator/Sentinel has **no systemd/launchd supervision** — everything else runs as an ad-hoc foreground process | No supervised service for the core scheduler | Stand up a real supervised process, or explicitly accept and document manual restart as the current model | 24x7 Watchdog (`sentinel.py`, labeled honestly per §2 of the plan) |
| 11 | Security Readiness | 75 | Verified, real pass completed | 2026-09-13: added missing CSP/X-Frame-Options/Referrer-Policy/Permissions-Policy headers (HSTS + nosniff were already present), tightened `Access-Control-Allow-Origin` from `*` to a real origin allowlist on blackboxops-os, confirmed no exposed secrets in client bundles or `.env`/`wrangler.toml` paths, `npm audit --omit=dev` clean (0 vulnerabilities) on both codebases, verified live checkout still works end-to-end after both changes (real browser test, zero console errors) | No full auth/session or rate-limiting review done yet | Review rate limiting on checkout/auth endpoints; re-run this pass periodically, not as a one-time check | Site Security Protector (`security.yaml`) |
| 12 | Bugfix/Failure Memory | 75 | Verified real, extension pending | `bugs`/`bug_events`/`patches`/`failure_analyses` tables confirmed by direct schema read, 2026-09-13; `dashboard/app/bugs` and `dashboard/app/failure-analyses` are real, live dashboard pages | `data/failure-memory.json` export doesn't exist yet; no `agent_id` column on `failure_analyses` | Build the export script described in the companion doc | Bugfixer & Troubleshooting (`bug_fixer.yaml` + `kaixen_bot.yaml`) |

## Reading this table honestly

- Nothing here is claimed at 100 without a specific, checkable piece of
  evidence in the row.
- Categories 4, 9, 10, 11 are real 50s — genuine infrastructure exists,
  but "exists" isn't the same as "verified working end-to-end," and this
  scorecard's whole point is not blurring that line.
- Category 2 (Product Range) at 50 is a deliberate reminder that the
  marketing page's "ten modules" framing is aspirational for 8 of them —
  worth keeping in mind before any outreach overstates what's live.
