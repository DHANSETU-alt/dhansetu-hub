# blackboxOps_OS Launch Checklist

Real status per item — checked or not, not assumed.

## Blocking (must resolve before any production step)

- [ ] **Identify which project is deployed as blackboxops.co.in** — asked three times, still genuinely unknown. Checked real accounts 2026-08-24: Railway (0 projects), Render (2 real services — `dhansetu-landing`, `dhansetu-planner`, both from `github.com/DHANSETU-alt/dhansetu-web` — neither matches blackboxops.co.in). Founder said "deploy right now in our system folder" (i.e. this dashboard) — see the new blocking item below before acting on that.
- [x] **Confirmed real pricing, 2026-08-24 — founder's decision.** Starter ₹6,999/mo, Growth ₹17,999/mo, live on the Pricing page. Real market research (small-agency/SMB AI agent pricing, 2026): narrow single-workflow bots start near $0-50/mo; agency-deployed multi-workflow agent teams run $300-1,500/mo/client in the US market — the wrong comparable to import directly since it prices out the actual target buyer (small Indian agencies). Landed at roughly 2-3x the old placeholder: fair market value, not bargain-bin, not mismatched to who's actually buying.
- [ ] **NEW, 2026-08-24 — real blocker found before any public deploy of this dashboard folder can happen.** `orchestrator/api.py` documents itself explicitly: "Local-only, no auth... not yet safe to expose beyond localhost." This dashboard's App Router serves the internal-only pages (Command Center, Finance, Security scan results, CEO decisions, Agent Registry) from the same Next.js app as the public blackboxOps_OS marketing/product pages, with zero authentication anywhere. Deploying this folder as-is to a public domain would expose all of that internal data publicly, not just the intended customer-facing pages. Needs a real decision before deploy: split the public pages into their own deployable app, or add real auth in front of the whole thing first.
- [ ] **Decide on Customer Portal scope** — real auth is a separate build; confirm whether launch waits for it or ships without it first.

## Built and verified

- [x] Live site backed up (`WEBSITE_BACKUP_REPORT.md`) — homepage, assets, real audit scores captured
- [x] blackboxOps_OS staging pages built and rendering (all 6 pages return HTTP 200, zero client-side console errors — checked with headless Chromium, not assumed)
- [x] Agent Visualization is the real Mission Control component, rebranded — verified with a live screenshot
- [x] Command Center and ERT Center read real live data (`/api/governor`, `/api/incidents`, `/api/workers`) — not mocked
- [x] Razorpay checkout call path tested (error handling confirmed: missing credentials return a clean 400, not a crash)
- [x] PayU hash formula independently verified against a hand-built reference string
- [x] Customer Portal's gap stated honestly on the page itself, not silently shipped as a fake login form
- [x] Full backend test suite: 306/306 passing after all of this session's changes

## Real, concrete fixes worth carrying into the real site regardless of the folder-identity question

- [x] **Done, 2026-08-24** — 5/5 security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy) now live on this internal dashboard's `blackboxOps_OS` staging pages (`dashboard/next.config.ts`), verified via a real HTTP response, not assumed. CSP is dev-permissive (`unsafe-eval` for Next.js Fast Refresh) vs. a strict production variant, switched automatically on `NODE_ENV`. **Still can't land on the actual live site** — these headers belong in whichever of the 5 candidate repos is real, and that answer is still open. Copy this same `headers()` block into that repo once identified.
- [ ] Add `sitemap.xml` and `robots.txt` — both real 404s on the live site today. Same blocker as above — not done on the internal dashboard since it's not a public-facing/indexed site.
- [x] **Answered, 2026-08-24 — read the actual bundled code, not guessed:** the live site's existing Razorpay integration (`razorpay-checkout-BLUXvEho.js`, from the backup) sells a single **one-time ₹9,999 product ("Workflow Clarity Sprint")**, not a subscription — a completely different product from blackboxOps_OS's proposed ₹2,999/₹7,999 *monthly* tiers. It also uses the *correct* secure pattern we should match: order creation and signature verification both happen server-side (`/api/razorpay/order`, `/api/razorpay/verify`), the key secret never reaches the browser — unlike this session's staging "Founder Test Mode" panel, which was explicitly built as a staging-only shortcut and was never meant to ship that way. One more real finding: the live checkout's own status text says **"Secure checkout powered by Razorpay · Test mode"** — the production site itself may currently be running Razorpay in test mode, not live. Worth confirming with the founder directly, not assumed.
  - **Recommendation:** don't extend the existing one-time-purchase integration — supersede it. It's built for a single ₹9,999 product; blackboxOps_OS needs recurring subscriptions, which needs Razorpay Subscriptions (already built and tested this session in `payment_gateway_manager.py`), not Payment Links. Keep its server-side-only credential pattern though — that part is worth copying into the real launch, not the founder-test-mode shortcut.

## Pending review, 2026-08-24 — founder decision made, not built yet

- [ ] **Customer Portal auth: email ID + password.** Reversed 2026-08-24 — founder's own words: "sorry for wrong decision" on the earlier Telegram-only call from the same day. Standard credential auth now, not Telegram login. **Explicit, non-negotiable requirement, unchanged from the earlier decision: user privacy must be protected "at any cost."** Applied to password auth: real hashing (bcrypt/scrypt/argon2, no plaintext ever, no plaintext in logs), secure httpOnly session cookies, real session expiry, and a clear one-line statement on the portal itself of exactly what's collected and why. Scope this properly before writing code — flagged for review, not started.
- [x] **Partially done, 2026-08-24 — PayU, real and live.** Founder provided a real PayU checkout link (`u.payu.in/xJYCpF9eG4sc`), created directly in their own PayU merchant dashboard. Verified genuine before wiring it in (traced the real redirect: `u.payu.in` → `payu.in/pay/...`, real PayU infrastructure). Live now on `/blackboxops-os/pricing` as its own "Live · Real PayU checkout" section, clearly separated from the Starter/Growth demo cards since it's a fixed-amount link that may not match either tier's price.
- [ ] **Razorpay — explicitly deferred by the founder ("forget Razorpay now, will update later").** Still zero real credentials, `.env.local` still doesn't exist. Server-side env-var path is built and tested, ready the moment real keys are provided — no further backend work needed.

## Done, 2026-08-24 — support email wired everywhere real

- [x] **`support@dhansetuhub.in` — founder-owned, real inbox.** Added as a single shared constant (`dashboard/lib/brand.ts`) and wired into every real customer-facing surface: blackboxOps_OS homepage footer, Portal page, Pricing page, PDF Studio, and the public Dhansetu AI bio-link page. Not yet able to *send from* this address — see Resend item below, still blocked on the founder completing OAuth.

## Paused, waiting on the founder specifically (not something I can push forward alone)

- [ ] **Resend OAuth for `support@dhansetuhub.in` sending.** Needs the founder to run `/mcp` → select "claude.ai Resend" → authorize in browser, then real DNS domain verification for `dhansetuhub.in`. Test email queued to send to `g4ever21@gmail.com` the moment this clears.
- [ ] **Real `ANTHROPIC_API_KEY` for Claude cloud escalation.** `orchestrator/model_gateway.py` / `config.py` already support it — deliberately opt-in, stays local-only (Ollama) until a real paid key is set. Founder flagged they answered an earlier question about this "without knowing" — not proceeding further until they actually want to pay for and provide a real key. No `.env.local` exists yet.
- [ ] **Confirm the real PayU link's price.** `u.payu.in/xJYCpF9eG4sc` renders its checkout client-side (JS) — can't be read by fetching it. Only the founder opening it can confirm the actual amount.
- [ ] **A real first outreach contact.** Sales/Marketing agents are ready to draft and send; no actual person has been named yet.

## Not yet started (real, not hidden)

- [x] **Done, 2026-08-24** — `/api/blackboxops/subscribe` now checks `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET`/`PAYU_MERCHANT_KEY`/`PAYU_MERCHANT_SALT` env vars first and ignores browser-supplied credentials the moment those are set — verified live both ways (no env vars: browser panel still required, unchanged; fake test env vars set: real call reached Razorpay's API using the env value, browser-supplied junk correctly ignored, response confirms `credentialSource: "server_env"`). `.env.local.example` documents the variable names; `.env*` already gitignored. Found and fixed a real adjacent bug while testing this: a gateway failure used to crash the CLI uncaught, leaking a full Python stack trace (file paths included) into the API response — now caught and returned as a clean error. Founder test mode panel is untouched and still works as the fallback when no env vars are set.
- [ ] A confirmed real deploy target and process — depends on the folder-identity answer
