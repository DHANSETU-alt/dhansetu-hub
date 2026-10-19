# DhanSetu Hub implementation status

Last verified: 2026-09-22 (Asia/Kolkata)

## Implemented in the local feature branch

- Mobile-first DhanSetu homepage, product navigation, legal pages, and partner disclosures.
- SmartBudget workspace with manual transactions, CSV import/export, duplicate fingerprints, safe-to-spend calculations, explainable LeakShield rules, and an authenticated sync API. Browser-local storage remains the safe fallback until the database migration is applied.
- Versioned deterministic Indian salary tax estimator for supported ordinary cases, with explicit unsupported-case flags and rule-source references.
- GST purchase-register/GSTR-2B reconciliation workspace with duplicate, missing, and value-mismatch review flags. It reports amount requiring review, not guaranteed recovery or filing.
- Entitled Resume AI PDF/DOCX extraction route. Uploads are limited to 5 MB, processed in memory, protected by authentication and entitlement checks, and not persisted by this feature.
- Partner, affiliate, expert, and licensed-partner application routes. Applications remain pending review; no automatic verification or payout is enabled.
- Founder-only revenue command center backed by server-side user-ID allowlisting and actual database rows only.
- Bounded daily research job restricted to approved official HTTPS sources, with deduplication, source dates, fingerprints, budget caps, and SSD guard.
- Automatic Razorpay entitlement flow, idempotent grant migration, receipt module, billing view, legal consent, and payment regression harness.
- Existing Supabase authentication now includes password-reset email flow, secure recovery-session password update, safe return-path validation, Google sign-in continuity, and explicit sign-out from Billing.
- SSD-safe Docker Compose, standalone Next server, systemd unit, backup/restore scripts, and exact verified SSD UUID template.

## Locally verified

- `npm run lint`: 0 errors; 2 existing warnings (`<img>` optimization and an unused suppression).
- `npm run typecheck`: pass.
- `npm test`: 5 files, 13 tests passed.
- `npm run build -- --webpack`: pass; all current routes generated.
- `npm run verify:payment`: 8/8 assertions passed, including idempotency, tamper rejection, concurrent seat limits, and unauthenticated denial.
- `npm audit --omit=dev --audit-level=high`: 0 vulnerabilities.
- Docker production image `dhansetu-hub:local`: built successfully.
- Missing-SSD Compose test: refused startup because `/mnt/dhansetu-data` did not exist and did not create the path.
- Local standalone smoke: `/`, `/partners`, `/api/health` returned 200; unauthenticated `/resume-ai` redirected to login.
- Production build includes `/auth/reset`; typecheck, lint, unit tests, and payment regression tests pass after the auth update.
- Production build includes `/api/smartbudget`; authenticated sync is locally verified at the route/build level, while live persistence remains unverified because the Supabase migration is not applied.
- Daily research smoke test succeeded in temporary storage: the first run produced one finding and the second produced zero duplicate findings, with digest and state artifacts written. Production execution remains SSD-guarded.
- External SSD read-only inspection: Kingston `/dev/sda1`, ext4, UUID `9e8acd1d-2da8-4593-9a90-3b3cd1af3968`; existing GVC/DhanSetu backup found; SSD was safely unmounted afterward.

## Live verified on `https://dhansetuhub.in`

- `/`, `/api/health`, `/smartbudget`, and `/tools` returned HTTP 200 during the latest smoke check.
- Live response included HSTS, `X-Content-Type-Options`, `X-Frame-Options`, and API `Cache-Control: no-store` headers.
- `/checkout` redirected unauthenticated users to login, but the live query still used the older `founding_lifetime` catalog. The latest local public catalog is not live.

## Blocked or unverified

- Local feature branch `feat/auto-activation-after-payment` is ahead of the remote feature branch. No push or deployment was performed; main was not changed.
- Render/Cloudflare cutover is not verified. The production host still serves the older release.
- Supabase migrations are files only and have not been applied to production `moneytrack`.
- Google OAuth provider configuration and a fresh production sign-in are not live-verified.
- Razorpay production webhook secret, end-to-end live test payment, and production entitlement grant are not live-verified.
- Stable SSD mount at `/mnt/dhansetu-data` is not configured. The SSD exists, but root-level `/etc/fstab`/mount authorization is still required.
- Supabase/Postgres remains the current database; full SSD database migration and restore test require a configured database dump credential and mounted writable SSD.

## Exact owner-gated actions remaining

1. Confirm the Kingston SSD identity, install `ops/dhansetu-fstab.example` as `/etc/fstab`, mount `/mnt/dhansetu-data`, and run `scripts/storage-guard.sh`.
2. Push the feature branch and authorize the Render deployment, then repeat live smoke tests.
3. Apply the reviewed Supabase migrations to a non-production project first, then production after backup and approval.
4. Configure Google OAuth redirect URIs and Razorpay webhook events/secrets in their owner dashboards.

No customer payment, entitlement, credential, DNS, or SSD filesystem change is claimed as complete until its live evidence exists.
