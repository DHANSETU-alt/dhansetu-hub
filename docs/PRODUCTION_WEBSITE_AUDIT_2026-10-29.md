# DhanSetuHub Production Website Audit — 2026-10-29

Target: `https://dhansetuhub.in/` and `https://www.dhansetuhub.in/`  
Auditor: Codex + ECC Guide, BrowserSkill read-only production smoke test  
Scope: public UI, authentication, UPI QR, checkout boundary, representative controls, origin/API evidence

## Executive verdict

**DO NOT advertise authentication or payment as fully operational yet.** The static site and Cloudflare proxy are healthy, but two owner-side configuration gates remain:

1. Firebase rejects the production domain with `auth/unauthorized-domain`.
2. No verified merchant VPA was supplied; the old placeholder `dhansetu@icici` was unsafe and has been removed from payment generation.

Razorpay checkout is intentionally account-gated. An unauthenticated visitor receives a redirect to `/login`; this is not a checkout success and must not be counted as payment evidence.

## Evidence

| Check | Result | Evidence |
|---|---|---|
| Apex HTTPS | PASS | `https://dhansetuhub.in/` → HTTP 200, `content-type: text/html`, `x-dhansetu-launch: aistudio-proxy-v3` |
| WWW HTTPS | PASS | `https://www.dhansetuhub.in/` → HTTP 200, same launch header |
| Static design | PASS | Live title: `The DhanSetu Chronicle — Private GST Invoicing, AI Copilot & Business OS` |
| Authentication | FAIL / external action required | Browser console and UI: `auth/unauthorized-domain`; Firebase explicitly says to add `dhansetuhub.in` and `www.dhansetuhub.in` to Authorized domains |
| UPI QR | FAIL-safe | Before patch it displayed `dhansetu@icici`; after patch live UI displays `MERCHANT VPA REQUIRED` and generates no QR until a founder-verified VPA is entered |
| Checkout unauthenticated | EXPECTED GATE | `/checkout?tier=all_access` → HTTP 307 → `/login?next=...` |
| Create order unauthenticated | EXPECTED GATE | `POST /api/checkout/create-order` → HTTP 401 `{"error":"Authentication required"}` |
| Health/config endpoint | CONFIG ONLY | `/api/health` reports payment configured, but `transactionVerified:false` |
| Payment verification endpoint | CONFIG ONLY | `/api/payment/verify-live` reports configured/live mode but explicitly says captured payment and signed webhook must be verified separately |
| Invoice editor | PASS | Live BrowserSkill click opened GST workstation modal with editable invoice fields |
| AI statutory audit | PASS | Live BrowserSkill click opened `GEMINI AI STATUTORY AUDIT REPORT`, `RISK: LOW` |
| Support link | PASS | Public UI exposes `mailto:support@dhansetuhub.in` |

## Root causes

### P0 — Firebase authorized-domain configuration

The client correctly initializes Firebase project `gen-lang-client-0041240540`, but the live Firebase Auth service rejects the request before Google OAuth can start. This is an account-side Firebase Console change, not a Cloudflare HTML bug.

Required owner action:

- Firebase Console → Authentication → Settings → Authorized domains
- Add `dhansetuhub.in`
- Add `www.dhansetuhub.in`
- If Google OAuth is separately restricted, add the same production origins to the Google OAuth client

After the change, re-run the live Google sign-in smoke test. Do not provide passwords, OTPs, or recovery codes to Codex.

### P0 — Placeholder merchant VPA

The exported AI Studio page hardcoded `dhansetu@icici`. That value was not verified as the founder’s account. The patch removes it from the default invoice state and makes QR/deep-link/print/pass actions fail closed until a valid VPA is supplied at runtime through `window.__DHANSETU_MERCHANT_UPI__`, local vault key `dhansetu_founder_upi`, or the visible UPI field.

Required owner action:

- Supply the exact verified merchant VPA and payee name
- Verify the payee identity in a bank/UPI app with a small test payment
- Only then place the VPA in the deployment runtime configuration

No guessed VPA (including examples from an automated audit) should be deployed.

### P1 — Razorpay status wording

The current server boundary is safer than a client-only checkout: it requires an authenticated user before order creation and verifies payment server-side. The public health endpoint saying `paymentReady:true` is a configuration signal, not a settled-payment proof. Production reporting must remain at ₹0 until a real signed capture, entitlement, refund/reconciliation record, and delivery evidence exist.

## Code changes shipped

- Commit `983ab82` (`fix static auth diagnostics and fail-closed merchant UPI`)
- Pushed to `main` and `codex-launch-20261019`
- Cloudflare Worker updated to pin commit `983ab82`
- Active Worker version: `407cf98e`
- Launch header: `x-dhansetu-launch: aistudio-proxy-v3`
- Firebase errors now show their exact code and corrective action
- Popup-blocked/closed cases have a redirect fallback; unauthorized-domain remains clearly surfaced
- Placeholder UPI is removed from runtime defaults and legacy local-vault drafts are normalized
- QR, copy-link, download, print, and pass actions are guarded by VPA validation

## Verification commands

```text
npm run typecheck
npm test -- --run
npm run test:security
npm run build
git diff --check
```

All passed at the time of this audit: 52 tests, 6 security checks, production build completed, and the worktree is clean.

## Sign-off gate

This audit can be upgraded from **DO NOT SHIP / configuration pending** to **READY FOR CONTROLLED PILOT** only after:

1. Firebase authorized-domain change is independently verified in the browser.
2. Founder-verified merchant VPA is configured and payee identity is checked.
3. One Razorpay test-mode order is created, captured, signature-verified, reconciled, and recorded.
4. No real payment or customer entitlement is reported from configuration-only endpoints.
