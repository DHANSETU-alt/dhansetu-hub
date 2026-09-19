# DhanSetu Hub Engineering Guide

## Architecture model

1. The application is Next.js 14 App Router with React 18, TypeScript, and Tailwind CSS.
2. Render is the intended Next.js runtime; API route handlers use the Node.js runtime.
3. Supabase project `moneytrack` owns authentication and PostgreSQL data.
4. Browser and server Supabase clients share auth cookies through `@supabase/ssr`.
5. Production sets `NEXT_PUBLIC_AUTH_COOKIE_DOMAIN=.dhansetuhub.in`, allowing the main site and `budget.dhansetuhub.in` to share the same Supabase session.
6. Checkout requires a verified Supabase user before any Razorpay order is created.
7. Prices and tier identifiers come only from `lib/payment/tiers.ts`; client amounts are ignored.
8. Payment verification re-fetches the Razorpay order and checks amount, currency, user, and tier.
9. Both browser verification and signed webhooks call the same PostgreSQL-backed idempotent entitlement function.
10. The welcome page polls entitlement for 60 seconds and redirects into the app; manual support is fallback-only.

## Non-negotiable payment invariant

One confirmed Razorpay payment grants access exactly once. The same customer must never be charged again because of a webhook delay, browser crash, redirect failure, provider timeout, or network interruption. Reconciliation is always idempotent: verify the payment with Razorpay, then retry the same entitlement grant using the unique payment ID. Payment confirmation is required before access; email alone is never sufficient.

## Commands

```bash
npm install
npm run lint
npm run typecheck
npm test
npm run build
npm run verify:payment
```

For a build without production secrets, provide placeholder-shaped values for the required server variables. Never commit those values.

## Payment flow

```text
Pricing → /checkout?tier=… → no session? /login?next=…
        → authenticated checkout + required legal consent
        → POST /api/checkout/create-order
        → server tier/price/seat/rate validation
        → Razorpay order + pending purchase
        → Razorpay handler
        → POST /api/checkout/verify ─┐
Razorpay signed webhook ────────────┤
                                    └→ validate fetched order
                                      → grant_lifetime_entitlement()
                                      → purchase paid + profile plan + seat count
                                      → receipt
                                      → /welcome polling → budget.dhansetuhub.in
```

## Conventions

- Secrets are server-only environment variables. Never prefix secrets with `NEXT_PUBLIC_`.
- Route handlers authenticate with `supabase.auth.getUser()`, never unverified session claims.
- Payment signatures use HMAC-SHA256 and constant-time comparison.
- Webhooks verify the exact raw request body before JSON parsing.
- Entitlement changes happen through the service-role-only PostgreSQL function.
- Database changes are migration files and are never applied implicitly.
- `PAYMENT_FLOW_TEST_MODE` is rejected in production and exists only for the local regression harness.

## Known pitfalls

- Latest Vitest required Node typings newer than this project. Root cause: unconstrained install selected Vitest 5. Fix: pin Vitest 2.1.9 for the Node 20 baseline.
- `@types/razorpay` returned registry 404. Root cause: the package does not exist; Razorpay includes typings. Fix: do not install it.
- TypeScript TS2802 rejected spreading `MapIterator` under the existing target. Fix: use `Array.from(map.values())`.
- The sandbox blocked tsx IPC socket creation. Fix: run `npm run verify:payment` with local process/socket permission.
- The harness initially used top-level await under CommonJS output. Fix: wrap lifecycle in `async main()`.
- Next route bundles could not share module-local test state. Fix: use a namespaced, test-only `globalThis` store; production always uses Supabase.
- Integrated build lint rejected `var` in a global declaration. TypeScript requires it for global augmentation; fix is one scoped ESLint exception on that declaration.
- `npm audit` can fail when registry DNS is unavailable. Re-run with network access and record the actual result; never claim a clean audit from a failed request.
