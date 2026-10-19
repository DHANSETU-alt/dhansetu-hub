# Performance evidence — 2026-09-26

## Findings

- The dashboard development server and orchestrator API were stopped after the
  Mac reached load averages of approximately 80–100 on an 8-core host.
- Paperclip's development runner was still compiling its Rust runner after
  roughly 13 minutes; a second forced dependency install was also active.
- Mission Control aggregates 11 local API calls. The shared auto-refresh
  default was one second, allowing refreshes to overlap that fan-out.

## Changes

- `dashboard/components/AutoRefresh.tsx`: safe default changed to 30 seconds.
- `dashboard/lib/systemStatus.ts`: aggregate status cached for 15 seconds with
  Next server cache to prevent overlapping fan-out requests.
- `scripts/mac_performance.sh`: read-only report plus narrowly scoped
  `--relieve` command for known DhanSetu/Paperclip development processes.

## Verification

- `npx tsc --noEmit`: passed.
- `npx next build --webpack`: passed compilation, TypeScript, 58 static pages,
  and optimization.
- `npm run build` using default Turbopack: failed because Turbopack could not
  create a worker port (`Operation not permitted`); production hosting should
  use the successful Webpack build path.
- Production `next start` smoke test: `/` returned HTTP 200 in 0.106s.
- `/mission-control` returned HTTP 500 while the orchestrator API was stopped,
  with the explicit cause `ECONNREFUSED 127.0.0.1:8787`; this is an honest
  integration blocker, not a connected-agent claim.

## Current state

No dashboard, orchestrator, Paperclip, or Hindsight listener was left running
after testing. The flow view must be reopened only after a bounded API/Paperclip
integration path is in place.
