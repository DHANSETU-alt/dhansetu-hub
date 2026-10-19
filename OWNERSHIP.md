# Ownership

**Owner: claude** — dhansetuhub.in app

Updated by the founder on 2026-09-26: the OpenAI/Codex subscription was cancelled, so Codex no
longer operates on this machine. Claude now owns both dhansetuhub.in and blackboxops.co.in and
may commit and deploy here. Authorised directly by the founder: "change read it, do perform on
it ... only you and my self is there for work".

Supersedes the 2026-09-21 split that gave dhansetuhub.in to Codex and blackboxops.co.in to
Claude. That rule existed because on 2026-09-19 two agents edited the same Worker config within
minutes of each other; the second deploy narrowed the site route and blackboxops.co.in served
403 to every visitor until it was caught.

**The lesson from that incident still applies with one agent:**

- One writer at a time. Never run two deploys of the same service concurrently.
- Run the full gate before any deploy: `npm run lint && npm run typecheck && npm test &&
  npm run build && npm run verify:payment`.
- A failed Render deploy leaves the previous deploy serving, so verify live routes after every
  deploy and treat the old deploy as the rollback until the new one is confirmed.
- Payment, DNS, customer messaging, deletion and database migrations stay founder-approved.

## Deploy notes learned the hard way

The Render service `dhansetu-hub` (`srv-danctvrbc2fs73dvv80g`) auto-deploys on commit from the
branch `feat/auto-activation-after-payment`.

Two failure modes have already cost a release:

1. **2026-09-21, `update_failed`.** The build succeeded and the app logged `Ready in 3.1s`, then
   Render reported `Timed Out`. The server was bound to `localhost`, so the external health
   check could never reach it. `next.config.mjs` now sets `output: 'standalone'` and the start
   command runs `.next/standalone/server.js`, which binds `process.env.HOSTNAME || '0.0.0.0'`.
   Never reintroduce a start command that binds loopback.
2. **Missing standalone assets.** `next build` does not copy `.next/static` or `public` into
   `.next/standalone`, so the server starts, passes the health check, and then 404s every
   stylesheet, script and image — a live site that looks broken rather than one that is down.
   The `postbuild` script copies both. Do not remove it.

Enforcement: `.git/hooks/pre-commit` refuses commits unless `GVC_AGENT` matches the owner.
Claude runs with `GVC_AGENT=claude`.
