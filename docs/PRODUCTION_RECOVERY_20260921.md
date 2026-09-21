# DhanSetu production recovery — 2026-09-21

## Verified changes

- Cloudflare confirmed deletion of apex A records `172.66.3.26` and `162.159.143.30`. Remaining apex record is `216.24.57.1`, proxied. Email records preserved. Removed records can be recreated from these recorded values.
- Submitted www A record `216.24.57.1`; HTTPS now responds 403 rather than failing DNS resolution. Domain activation is not complete.
- Razorpay confirmed a new enabled webhook at `https://dhansetu-hub.onrender.com/api/webhooks/razorpay` for `payment.captured` and `order.paid`.
- Matching RAZORPAY_WEBHOOK_SECRET is saved in Render's environment. No secret values belong in this document.
- Commit d1bbbdd makes /api/health dynamic and requires every configured dependency, including the Supabase service role credential. Prior responses were generated at build time.
- Build, typecheck, 4 unit tests, and all 8 payment harness assertions passed.
- Render deployment `dep-daoatmv40ujc73ej79vg` built successfully; last observed rollout state: Deploying. Old release remains live until rollout completes.

## Remaining work

1. Verify Render rollout to d1bbbdd; confirm fresh timestamps and webhook configuration.
2. Configure SUPABASE_SERVICE_ROLE_KEY privately in Render. Browser clipboard transfer did not populate the field; no successful save is claimed.
3. Verify database migrations/functions and perform authenticated entitlement checks. No production migrations were applied in this run.
4. Complete Render custom-domain verification/certificates and check Cloudflare routing. Apex /api/health still returned the old application's 404 after DNS cleanup; no Worker routes were configured.
5. Verify checkout, callback, signed webhook processing, and existing purchaser access. No live payment or real entitlement grant was performed.

## Coordination evidence

ECC security-reviewer instructions were read and applied to credential handling and payment verification. Ruflow task `task-1789935341693-etg444` records this recovery. Ruflow agent list returned no active agents; task creation is not proof of an executing external worker. Codex performed the work.

## Browser observations

Some native clicks reported success without changing the page. Fresh observations and targeted UI button activation were needed. Do not blindly repeat mutations or reuse stale refs. A browser session disappeared mid-task and was replaced only after checking the connected browser and session state.
