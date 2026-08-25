# Production Cutover Plan

**This plan describes what will happen. Nothing in it has been executed. No production system has been touched, modified, or deployed to.** Every step below is gated on the founder-identity question and explicit approval — per the mission order's own instruction, this is intentional.

## Precondition (blocking, not yet met)

Step 0, before anything else: identify which local project (`dhansetu-hub-live`, `dhansetu-pdf-studio`, `dhansetu-peopledesk`, `partner-roadmap`, `public-landing`) is the real source for blackboxops.co.in, and confirm access to its actual deployment mechanism (Cloudflare Pages? A Git-push-to-deploy flow? Manual?). Nothing past this point can be executed without it — not because of caution for its own sake, but because "cut over" requires a real, known target to cut over *to*.

## Sequence, once the precondition is met

1. **Re-verify the backup is current.** `WEBSITE_BACKUP_REPORT.md`'s snapshot is from the day it was taken — re-run it immediately before cutover, not days after, in case the live site changed in between.
2. **Confirm the identified project's own local dev server runs cleanly** — `npm install`, apply the Gatekeeper `postinstall` fix already added to all 5 candidates (real, done, this session), `npm run dev`, manually verify it matches the live site.
3. **Merge or replace** — decide whether blackboxOps_OS's new pages (Command Center, Agent Visualization, ERT Center, Pricing) get added into the identified project as new routes, or whether the identified project's existing homepage gets replaced outright. This is a real product decision, not a technical one — flagging it rather than picking silently.
4. **Wire real merchant credentials server-side** — environment variables on whatever hosts the identified project, never the founder-test-mode panel built for staging. That panel was explicitly built to be replaced, not deployed.
5. **Real payment gateway test in the identified project's own staging/preview environment** (Cloudflare Pages preview deploys, if that's the real hosting — consistent with the `wrangler`/`@cloudflare/vite-plugin` dependencies found in all 5 candidates) — a real transaction, in test mode, before anything touches the production domain.
6. **DNS/deploy cutover** — whatever the identified project's real deploy command is (`wrangler deploy`, a Git push, a dashboard button) — executed once, with the founder present, not automated into this pipeline. This is the one step in the entire blackboxOps_OS effort with real, hard-to-reverse consequences (a live domain, real customers, real money) — it gets a human hand on it, deliberately, every time.
7. **Post-cutover verification** — re-run the real WEB-001 audit (`website_audit.run_website_audit`) against the live domain immediately after cutover, confirm scores match or exceed the pre-cutover baseline, confirm the real checkout flow works end-to-end with a real (small, refundable) transaction.
8. **Keep the old version reachable** for a defined rollback window — "DO NOT DELETE EXISTING SITE YET" stays true even after cutover, not just before it, until the new version has been live and stable for a real observation period.

## What this plan deliberately does not do

It does not pick a rollback window length, a specific hosting migration path, or a go-live date — those are founder decisions this plan surfaces rather than makes. A migration plan that silently decided them would be making calls that aren't mine to make.
