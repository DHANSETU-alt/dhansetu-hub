# Automatic payment activation

## Runtime flow

The customer signs in or signs up before checkout. `/checkout` preserves the selected tier through the `next` query parameter. Production cookies use the parent domain `.dhansetuhub.in`, so the authenticated session is available to both the storefront and `budget.dhansetuhub.in`; no token is placed in a URL.

`POST /api/checkout/create-order` authenticates the user, applies a database-backed rate limit, validates the tier against the server catalog, checks remaining seats, stores consent metadata, and creates the Razorpay order with `user_id` and `tier` notes.

Razorpay can confirm payment through either path:

- `POST /api/checkout/verify` checks `HMAC_SHA256(order_id|payment_id, key_secret)` with constant-time comparison.
- `POST /api/webhooks/razorpay` checks `X-Razorpay-Signature` against the untouched raw request body using the webhook secret.

Both paths fetch the order from Razorpay, validate its amount, currency, user, and tier against server records, then call `grantEntitlement`. The PostgreSQL function locks the purchase, enforces the seat limit atomically, records the unique payment ID, and updates the profile plan. Duplicate delivery is successful but does not consume another seat.

## Strict no-repeat-charge rule

After the first confirmed payment, the customer must never pay again to recover access. Browser failures, webhook delays, provider timeouts, and network interruptions are recovery cases, not new checkout cases. Reconciliation must fetch the existing Razorpay payment, require captured/paid status and trusted order details, and retry the same idempotent entitlement grant keyed by the unique payment ID. An email address by itself cannot grant access, and a missing entitlement must never trigger a second charge.

After browser verification, `/welcome?order=…` polls `/api/entitlement` every two seconds. Active accounts redirect to `NEXT_PUBLIC_APP_URL`. Support instructions appear only if activation has not completed in 60 seconds.

## Tables and functions

- `purchases`: account, tier, Razorpay references, trusted amount/currency, status, legal consent, timestamps. Payment and order identifiers are unique.
- `tier_seats`: seat limit and atomically incremented sold count per tier.
- `checkout_rate_limits`: short-lived server-only checkout attempt records.
- `profiles.plan` and `profiles.lifetime_since`: server-managed entitlement state.
- `grant_lifetime_entitlement(...)`: service-role-only idempotent transaction.
- `check_checkout_rate_limit(...)`: service-role-only rate-limit transaction.

RLS permits authenticated users to read only their own purchases. Browser roles cannot write purchases or entitlement fields.

## Razorpay test-mode verification

1. Create Razorpay test keys and a test webhook secret.
2. Set all variables from `.env.example` with test values.
3. Apply the migration to a non-production Supabase branch/project.
4. Set the webhook URL to `https://<test-host>/api/webhooks/razorpay` and enable `payment.captured` and `order.paid`.
5. Start the app with `npm run dev`, create a Supabase test account, and complete a Razorpay test payment.
6. Confirm `/welcome` redirects, `/billing` contains one paid record, and `profiles.plan` is `founding_lifetime`.
7. Run `npm run verify:payment` for the keyless regression suite. It generates valid and invalid HMACs and verifies authentication, idempotency, tamper resistance, and concurrent seat limits against a local-only backend.

The automatic-entitlement migration is applied to the linked `moneytrack` project. Production deployment still requires the application host to be authorized and configured.
