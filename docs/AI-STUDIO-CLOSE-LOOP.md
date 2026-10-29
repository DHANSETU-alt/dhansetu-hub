# AI Studio → DhanSetu close loop

The AI Studio export is preserved at `/aistudio/` as an isolated redesign preview. The existing Next.js application remains the system of record for authentication, checkout, Razorpay verification, webhooks, and entitlements.

## What is wired locally

- AI Studio's 295 KB `index.html` is available from the same origin at `/aistudio/`.
- Its AI actions call bounded local adapters at `/api/ai/reminder-tone`, `/api/ai/suggest-hsn`, `/api/ai/audit-invoice`, `/api/ai/analyze-expenses`, and `/api/ai/parse-form16`.
- The Founder Pass CTA routes to `/checkout?tier=all_access`; it does not fake a payment or grant access in the browser.
- The existing payment boundary remains authoritative: authenticated user → server-owned tier price → Razorpay order → signed browser/webhook verification → idempotent entitlement.
- Razorpay's configured `https://dhansetuhub.in/api/razorpay/webhook` URL is supported through a compatibility alias to the canonical `/api/webhooks/razorpay` handler; both paths use the same raw-body signature check.
- The homepage exposes a `Chronicle redesign` link without replacing the existing authenticated workspace.

## Deployment boundary

Cloudflare Pages' direct-upload instructions apply only to a genuinely static export. This export still uses Firebase/D3 modules and same-origin AI endpoints, so it must be served from the Next.js application (or bundled with a build and equivalent API runtime). Do not upload the raw file as the production root until the build and API contract are verified.

## Required evidence before production cutover

1. Local typecheck, tests, and production build pass.
2. `/aistudio/` loads from the deployed origin and all five AI adapter calls return JSON.
3. Razorpay test order, checkout, captured-payment verification, duplicate webhook, and reconciliation evidence pass.
4. Cloudflare Pages project, custom domain, HTTPS, HSTS/CSP, and DNS records are verified in the authenticated dashboard and from an external request.
5. Only after those checks should the existing homepage be replaced or a Pages project be pointed at `dhansetuhub.in`.

Never store Razorpay secrets, Supabase service-role keys, or OAuth access tokens in `public/` or the repository.
