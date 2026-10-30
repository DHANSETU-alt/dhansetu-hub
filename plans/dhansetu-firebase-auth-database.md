# DhanSetu Firebase Auth + Database Recovery Blueprint

**Status:** blocked at provider configuration; local source remains deployable
**Date:** 2026-10-30
**Scope:** DhanSetuHub GST/tax application, authentication, persistence, usage analytics

## Current evidence

- The production Next.js service is live on `https://dhansetuhub.in`.
- Public routes and `/api/health` return HTTP 200.
- `nvtpsqtmroikuqdzozdt.supabase.co` returns DNS NXDOMAIN.
- `budget.dhansetuhub.in` returns DNS NXDOMAIN.
- The signed-in Firebase console account cannot access project `gen-lang-client-0041240540`.
- The application currently uses Supabase Auth plus Supabase Postgres/RLS for customer identity and data.
- The public AI Studio asset contains a separate Firebase client-only integration for Sheets sync; it is not a server authentication boundary.

## Decision

Keep Supabase as the authoritative customer database and authentication boundary until its project is restored or a replacement is explicitly selected. Add Firebase Authentication only as a separately verified provider for the founder/Google workflow after a Firebase project owned by the founder is available. Do not run two independent customer identity systems or silently migrate IDs.

## Why this is the safe design

1. Existing tables use Supabase Auth UUIDs and RLS policies. A Firebase UID cannot be substituted without a migration and identity-link table.
2. A dual-login implementation without a server-side token bridge would authenticate the browser but leave protected API routes unauthenticated.
3. Firebase Admin credentials are server-only and must be provisioned in Render Secret Files/Environment, never in the browser or Git.
4. Usage analytics should be first-party, consent-aware, and non-PII; it must not depend on a dead hostname.

## Ordered construction steps

### 1. Provider recovery (owner-gated)

- In Supabase, resume/confirm project ref `nvtpsqtmroikuqdzozdt`.
- If deleted or replaced, record the new ref and migration source before changing Render.
- In Firebase Console, select an owned project or create one explicitly; enable Email/Password and Google providers.
- Add `dhansetuhub.in`, `www.dhansetuhub.in`, and the Render preview host to Firebase Authorized Domains.

### 2. Database contract

- Apply the existing Supabase migrations first.
- Add an `analytics_events` table with: `id`, `occurred_at`, `event_name`, `path`, `session_hash`, `metadata`, and retention policy.
- Restrict inserts to an authenticated/anonymous ingestion policy with validated event names and bounded metadata.
- Keep founder dashboard queries aggregate-only; never expose customer emails or payment secrets.

### 3. Firebase founder bridge

- Add `firebase-admin` server dependency and server-only configuration:
  `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`.
- Add `POST /api/auth/firebase/session` to verify an ID token, enforce issuer/audience, and set a short-lived httpOnly session cookie.
- Add a `founder_identity_links` table mapping Firebase UID to the existing founder Supabase UUID.
- Permit Firebase sessions only for founder Sheets sync and analytics views; customer billing/data routes remain Supabase-authenticated until an explicit migration.
- Add CSRF/origin checks, secure cookies, rotation, revocation handling, and audit logging.

### 4. Analytics

- Add a privacy-safe client event collector with an allowlist (`page_view`, `tool_open`, `gst_reconcile_complete`, `login_started`, `checkout_started`).
- Hash the session identifier with a server-side salt; do not store raw IP, email, payment IDs, or document contents.
- Add founder-only aggregate cards: sessions, tool opens, GST reconciliations, auth starts, checkout starts, and last event time.
- If analytics storage is unavailable, show `analytics unavailable` rather than zero.

### 5. Domain and deployment

- Standardize application links on `https://dhansetuhub.in` until the `budget` CNAME is verified.
- If the subdomain is retained, add Render custom domain and Cloudflare CNAME, then verify DNS from two resolvers.
- Redeploy only after provider health, migrations, and environment names are validated.

## Verification gates

- `npm run typecheck`
- `npm test`
- `npm run test:security`
- `npm run build`
- `BASE_URL=https://dhansetuhub.in npm run release:check`
- Browser QA: login page, GST workflow, analytics dashboard, and unauthenticated API boundaries.
- Provider checks: Supabase health endpoint resolves; Firebase sign-in returns a verified ID token; Render health reports the expected provider refs without exposing secrets.

## Rollback

- Disable Firebase bridge flag and remove its session cookie path.
- Keep Supabase auth/data routes unchanged.
- Revert only the bridge migration after exporting analytics aggregates.
- Do not delete the existing Supabase project or tables during fallback.

## Explicit blockers

This blueprint cannot be marked complete until the owner authenticates to a Firebase project that exists and restores/confirms the Supabase project. No provider credentials are stored in this repository.
