# DhanSetu checkout readiness repair

## Source and live evidence

Baseline: `be0d39f7fafa5bc1bedc300e502b097a3bdc08a9` on `codex-launch-20261019` in `DHANSETU-alt/dhansetu-hub`.
The branch homepage matches the observed live domain: Intelligent Performance stage, three service cards, Plans/Contact/Sign in links.
The earlier Sites project is a different application; its successful deployment is not proof that the current custom-domain application changed.

Observed on 19 October 2026:
- Browser loaded `https://dhansetuhub.in/` and `/pricing`.
- Public pricing displayed Free, SmartBudget Pro at INR 149 once, and All Access at INR 399 once.
- Pro checkout navigated to sign-in, preserving the requested tier in `next`.
- `/api/payment/verify-live` reported live=true based only on secret presence; this is insufficient evidence of merchant activation or a successful transaction.
- HTTP headers included `x-render-origin-server: Render`; this identifies the responding origin but does not establish current service configuration.
- Some command-line requests received HTTP 403/error 1010. This is not evidence of application downtime.

## Changes

- Restore covered paid purchases instead of creating another Razorpay order.
- Check all covered unresolved orders before reusing any unpaid order; fetch the matching captured payment and retry the idempotent entitlement grant before returning recovery.
- Reconcile the authenticated user's order while polling the recovery page, so failed browser callbacks and delayed webhooks do not require a second checkout.
- Preserve an upgrade path from Pro to All Access.
- Guard duplicate clicks and Razorpay script readiness; recover from failed network/JSON requests.
- Continue account recovery after browser verification interruptions rather than encouraging another payment.
- Require the provider order status to be paid before granting entitlement.
- Retry account polling after transient network errors, cancel on unmount, and show Billing/support with the order reference after timeout.
- Separate configuration, test/live key mode, and transaction verification in health responses; remove hard-coded claims of successful webhooks and DNS fixes.
- Preserve the homepage design, pricing amounts, database schema, auth provider and payment credentials.

## Verification and limits

`npm test`: 48 tests passed, including direct mocked route tests for purchase restoration, pending-order reuse, bundled access and server prices.
`npm run lint`: no errors; three existing warnings (fonts, image element, unused eslint directive).
`npm run typecheck`: passed after correcting the browser timer type.
`npm run build`: passed, including standalone output and postbuild asset copy.
`npm run verify:payment` could not start through the tsx CLI due to an IPC socket permission error. An alternative invocation did not produce a completed harness result. Neither counts as a pass.

No real customer account was used, no charge was made, and captured-payment/webhook/receipt delivery were not verified against production services.
Render access is now verified in the user-confirmed workspace. The existing `dhansetu-hub` service (`srv-danctvrbc2fs73dvv80g`) tracks `codex-launch-20261019`, with commit-triggered automatic deploys, `npm ci && npm run build`, `npm start`, and `/api/health`. The recorded rollback deployment is `dep-dbb1c6ajnfac739h5rd0` at the baseline revision. Release monitoring and transaction verification remain separate gates.

## Release procedure

1. In the existing hosting service, confirm domain, repository, deployed branch and revision. Do not create another service or change DNS from this evidence alone.
2. Record the current deployment ID/revision as the rollback target.
3. Verify the existing Supabase URL/anon/service-role configuration and payment migrations without printing secret values. Verify live Razorpay keys and webhook secret on this same service; the separate Sites environment is not applicable.
4. Confirm the Razorpay webhook targets `/api/webhooks/razorpay` and the expected Google/Supabase callback URLs remain configured.
5. Deploy the tested commit using the existing service's build/start commands. The repository provides `npm run build` and `npm start`; start uses `.next/standalone/server.js` and `HOSTNAME=0.0.0.0`.
6. Verify health, homepage design, sign-in and both checkout tiers. Complete a controlled merchant test outside the agent browser as required for final payment authorization; verify captured status, webhook activation, refresh recovery and Billing.
7. Confirm repeat checkout restores access without another charge.

## Rollback and stop

No database migration is included. Roll back to the recorded prior deployment/revision in the same hosting service; retain payment records and webhook processing. Stop or suspend through that existing service's hosting controls only after assessing customer impact. For an already-authorized local host, `scripts/selfhost.sh stop` stops its existing Docker Compose deployment; it is not a Render control.
