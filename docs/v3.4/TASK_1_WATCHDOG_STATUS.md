# Task 1 Watchdog Status — DhanSetu AI Budget Tracker + LeakShield

Date: 2026-09-13
Product: DhanSetu SmartBudget + LeakShield™ on dhansetuhub.in
Repo: `/Users/apple/Documents/ChatGPT/box AI/dhansetu-hub-live` (real canonical repo, confirmed by response-header match against the live site — see [[project_dhansetuhub_live_engineering_audit_2026-09-11]])

## Current readiness

Can market today: **YES** — homepage, hero, feature grid, FAQ, pricing, lead form and a real payment flow are all already live at dhansetuhub.in. Real caveat below on signup. **Analytics are now wired** (GA4 `G-1JKQM3X4XL`) and **pricing is now confirmed LIVE in production** — a direct `curl https://dhansetuhub.in/` (and `/resume-ai`, `/terms`) this session shows zero remaining "₹99" text anywhere, only the real ₹0/₹149/₹399 tiers. This went live via the ChatGPT Sites builder chat (a separate publish path from this git branch), not via git push.
Can collect leads: **YES** — `JoinForm` on the homepage POSTs to `/api/waitlist`, backed by a real D1 `waitlist` table. Working today, zero changes needed.
Can accept payment: **YES, but two real gaps remain — see top blockers** — real Razorpay checkout is live with the new ₹149/₹399 tiers, confirmed live. **The Resume AI free-prompt-leak fix (commit `ee9a53d`) is written and test-passing but NOT yet live** — see top blocker #1.
Can deliver manually: **YES** — SOP written this session (`TASK_1_DELIVERY_SOP.md`). No blocker to walking a customer through onboarding by hand today.

## Top blocker

**#1 (most urgent, live revenue leak right now): the Resume AI prompt-leak security fix is written but blocked from publishing.** Commit `ee9a53d` moves prompt generation server-side behind a real payment check (all 5 tests pass locally). Two publish attempts via the ChatGPT Sites builder chat both failed with a real `403 Invalid or expired token` error from the Sites source-repository authorization — confirmed not transient (a fresh token was rejected immediately on retry). **Until this publishes, the free-prompt-leak bug is still live in production right now** — anyone can still get paid Resume AI prompts for free. Founder action needed: re-authenticate/reconnect the "Dhansetu Hub" site's source-repo connection at chatgpt.com/sites, then ask for the publish to be retried.

**#2 (blocks new signups, not existing users): Google sign-in is broken in production.** SmartBudget requires sign-in before a user can add a single transaction, budget, or reach LeakShield. Per prior verified diagnosis (`project_payu_rollout_status` memory, 2026-08-31), a real end-to-end sign-in attempt fails every time with Google's own `invalid_client` / "The provided client secret is invalid" error at the token-exchange step — confirmed not a code bug (redirect_uri, session logic, DB are all fine). This was not re-verified live this session — do one real sign-in attempt against the live site before any outreach push, to confirm whether this is still broken.

Second, structural blocker (lower priority, does not block marketing): **local repo is 5 commits ahead / 22 commits behind `origin/main`.** The 22 origin-only commits contain real, currently-live work (Razorpay checkout wiring, the current Google-auth setup, a full "neon liquid-glass" visual redesign, Resume AI launch) that never made it into local `main`. The 5 local-only commits (PayU checkout work, a Supabase-auth-era fix, a transaction edit/delete auth fix, a CSP fix) predate that redesign and were never reconciled. This session did **not** attempt to merge or resolve this — that's a real code-integration decision with production risk (touches both payment and auth on both sides), explicitly outside the low-risk "decide and proceed" list. All new work this session was done on a fresh branch `task1-leakshield` cut from `origin/main` (the real live tip), left uncommitted-to-origin, so it doesn't inherit or worsen this divergence.

## Next fix

Founder (or next session with Google Cloud Console access) confirms whether the Google sign-in `invalid_client` error is still live, and if so, resets/re-enters the real `GOOGLE_CLIENT_SECRET` in the Sites host's env vars for this project. This is the single highest-leverage fix available right now — it directly unblocks every other "YES" above from actually converting a real visitor.

## Needs founder approval

1. **Google sign-in secret fix** (`auth secrets` — explicitly high-risk, cannot be done by an agent).
2. **Reconciling the local/origin git divergence** — a real merge/integration decision touching payment and auth code on both branches; not attempted this session.
3. ~~Pricing model decision~~ — **RESOLVED this session.** Founder explicitly asked for "price range... one time not subscription wise." Shipped a real 3-tier one-time structure (see "What changed" below) replacing the flat ₹99 bundle. Still needs founder sign-off on the actual amounts (₹149 / ₹399) before this goes live, since nobody has confirmed those specific numbers — they're this session's defensible-but-unconfirmed judgment call, not a founder-given figure.
4. **Pushing the `task1-leakshield` branch to production** — no push credentials exist for `git.chatgpt-team.site` in this environment (separate, already-tracked blocker); someone with real credentials needs to push and publish via chatgpt.com/sites before LeakShield *or* the new pricing goes live for real customers.

## Build/test result

Real, run this session on the `task1-leakshield` branch (latest commit `e216a2a`, the Kaizen pass, on top of `497b976` → `0f60aa9` → `7132986`):
- `npm run build` → **pass** (`vinext build`, all routes compiled, `/api/leakshield`, `/api/resume-ai/prompt` all real recognized routes)
- `npm run lint` → **pass**, zero eslint errors
- `npm test` → **pass**, 5/5 tests green
- Prompt-leak fix independently verified by grepping the actual built output, not just reasoning about the code: `grep -rl "senior resume strategist" dist/client` → zero matches (exit code 1); the same phrase is present only in `dist/server/...` (the API route's server bundle) and `lib/resumePrompts.ts` (the new server-only source module). Confirms the real prompt-engineering templates no longer ship to the browser at all, paid or not.
- LeakShield math sanity-checked with a synthetic 10-transaction dataset via `npx tsx` — all four signal types (overspending, subscription detection, low-savings, cash-flow risk) fired correctly and `totalPossibleSavingsThisMonth` summed correctly. Not yet checked in a real browser (no browser tool available to this fork this session).
- Kaizen pass's 10 fixes verified via a mix of `curl` (PeopleDesk's real 401), `grep` (dead-asset references, zero remaining), and the same build/lint/test run above — see `SHAKTHI_FIX_LOOP_LOG.md` for the full per-item list.

## Next 3 actions

1. **Founder**: do (or ask someone to do) one real Google sign-in attempt on the live dhansetuhub.in SmartBudget flow — confirm whether it's still broken, and if so fix the `GOOGLE_CLIENT_SECRET` value in the real hosting env.
2. **Founder/next session**: reconcile the git divergence (decide which side's payment/auth work is authoritative) before anyone tries to push further changes — do this before, not after, pushing `task1-leakshield`.
3. **Next session with a browser tool**: once signed in as a real test user, add a handful of real transactions across 2-3 months and visually confirm the new LeakShield tab in `/smartbudget` renders correctly (empty state, then real alerts) before this goes live to paying customers.

## What changed this session

- Built real LeakShield detection logic (`lib/leakshield.ts`) and a real API route (`app/api/leakshield/route.ts`): overspending vs budget, recurring-charge/subscription detection, low-savings-rate warning, rising-cash-flow-risk detection — all computed from a user's actual `transactions`/`budgets` D1 rows, never fabricated.
- Wired a real "LeakShield" tab into the authenticated SmartBudget app (`app/smartbudget/smartbudget-app.tsx`) with an honest insufficient-data empty state.
- Updated the homepage's LeakShield nav marker from locked/"ROADMAP" to "LIVE" (`app/page.tsx`) — it's now true.
- **Pricing redesign (commit `0f60aa9`)**: replaced the flat ₹99 "All Access" bundle with a real one-time price range, per the founder's explicit follow-up instruction. New structure:
  - **Free** — ₹0 — 300 manual entries/month, budgets, reports (unchanged).
  - **SmartBudget Pro** — ₹149 one-time — unlimited entries + full LeakShield™ (the actual Task 1 product, now purchasable standalone for the first time; previously only bundled).
  - **Dhansetu All Access** — ₹399 one-time (was ₹99) — SmartBudget Pro + Resume AI.
  - All plans `billing: "one-time"` in `lib/razorpay.ts`'s `PLANS` table — the old `"smartbudget-pro-monthly"` entry (dead config, never actually purchasable, `billing: "monthly"`) is gone entirely. Zero recurring/subscription billing anywhere in the codebase now.
  - **Honesty fix bundled in**: the old bundle copy implied PDF Studio and PeopleDesk were paid perks of All Access. Both are actually separate free external tools with zero gating of their own (confirmed: they're plain outbound links, no auth/payment check). Copy on the homepage and Resume AI page now says this plainly instead of overselling what payment unlocks.
  - `PRO_PLAN_IDS` centralized in `lib/razorpay.ts` (was a locally-duplicated literal array in `app/api/transactions/route.ts`).
  - **Not done**: `resume-ai-lifetime` (₹299, standalone) stays defined but non-purchasable, exactly as before — wiring it up as its own independent SKU would require also rewiring Resume AI's own existing-access check, which was judged out of scope for a pricing-copy task.
  - **Unconfirmed by the founder**: the specific amounts ₹149 and ₹399 are this session's reasoned judgment call (roughly: old ₹99 bundle price plus a premium for now being 2 real gated products instead of a 4-tool overclaim), not numbers the founder gave directly — flag for a quick founder sanity-check before this goes live.
- Did **not** touch Razorpay verify/webhook logic (both are plan-id-agnostic, no change needed), Google auth code, or attempt to push/deploy anything — all explicitly high-risk/founder-decision territory.
- All work is on branch `task1-leakshield`, commits `7132986` (LeakShield), `0f60aa9` (pricing), then the prompt-leak + legal-copy fix (this entry), not pushed (no credentials) and not merged into local `main` (which keeps its own 5 unpushed commits untouched).

**Resume AI revenue-leak fix (founder-reported, this session)**: the founder found that anyone could get the real paid prompts without paying. Confirmed: `app/resume-ai/page.tsx` rendered the full generated prompt in a `<pre>` block regardless of `hasAccess`, and — because the page was a `"use client"` component — the entire `buildPrompt()` template logic shipped in plain JS to every visitor's browser before any interaction at all. There was no server-side secret; the "paywall" only gated the Copy button's clipboard call, not the visible/downloadable content.
- **Fix**: moved `buildPrompt()` into a new server-only module `lib/resumePrompts.ts` (never imported by a client component) and added `app/api/resume-ai/prompt/route.ts` — a POST route that checks real access (owner email, or a `payments` table row with `status: "paid"` on `dhansetu-all-access-lifetime`/`resume-ai-lifetime`) before returning the real prompt text; unauthenticated/unpaid requests get a 403 with a generic message, never any real template text.
- `app/resume-ai/page.tsx` now only shows a generic locked-preview string until a real fetch to that route succeeds using the same email captured during the existing Razorpay access-check flow; the Copy button copies the server-fetched text, never a locally computed one.
- Verified against the actual build output (see Build/test result above), not just the source — zero real prompt text in `dist/client`.
- Updated the hero copy's "your information stays in your browser" claim, which was no longer true once paid users' typed fields are sent to the server to generate their prompt — now reads "your details are sent only to generate your unlocked prompt and are never stored" (accurate: the route reads and returns, it does not persist request bodies).

**Legal copy re-review ("re-review payment terms as per services", founder's instruction)**: `app/terms/page.tsx` and `app/refunds/page.tsx` both still described the old flat ₹99 single-SKU pricing contractually. Rewrote both to reflect the real current one-time tiers (Free / SmartBudget Pro ₹149 / Dhansetu All Access ₹399, all one-time, none recurring), to state plainly that PDF Studio and PeopleDesk are free and not gated by any paid tier, and to describe LeakShield™ and Resume AI's actual behavior (pattern-review only, no savings/outcome guarantees; Resume AI produces a prompt for the user's own AI assistant, not a generated resume itself). Dated 13 September 2026.

**Kaizen pass ("do Kaizen on Web Site", founder's instruction, this session, commit `e216a2a`)**: found and fixed 10 real problems via direct code reading and `curl` (not invented busywork) — see `SHAKTHI_FIX_LOOP_LOG.md` for the full write-up of each. Headline items: Resume AI's back-to-home link was logo-only and unlabeled (fixed, the founder's original complaint); the homepage's dashboard preview showed specific fake numbers with no "sample data" label (fixed — now says so, matching the honesty bar the rest of the site already holds); `/smartbudget` was missing from the sitemap entirely; PeopleDesk's "Live" badge was corrected to "Early Access" after `curl` confirmed its real linked URL 401s; SmartBudget's LeakShield tab could get stuck on "Loading…" forever if the API call failed (fixed with a real error+retry state); none of the site's 3 modals closed on Escape (fixed); 1.25MB of dead public assets removed; added a branded 404 page and per-page metadata to 4 pages that were all sharing the homepage's exact title. Real GA4 analytics (`G-1JKQM3X4XL`) wired into `app/layout.tsx` in the same pass, closing the "zero analytics in production" gap a live-site audit found earlier this session.
