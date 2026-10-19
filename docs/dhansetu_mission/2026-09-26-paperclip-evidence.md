# Paperclip integration evidence — 2026-09-26

## Source and location

- Source: `https://github.com/paperclipai/paperclip.git`
- Local service checkout: `/Users/apple/shakthi-services/paperclip`
- Service branch/commit were preserved in the initial inventory; the checkout
  remains separate from the canonical DhanSetu repository.

## Startup repair

The full `dev:once` runner attempted to compile Paperclip's Rust runner and
caused unacceptable Mac load. The supported server-only path was used instead:

```bash
PATH=/Users/apple/shakthi-services/bin:$PATH corepack pnpm \
  --filter @paperclipai/plugin-sdk build
PATH=/Users/apple/shakthi-services/bin:$PATH corepack pnpm dev:server
```

Building `@paperclipai/plugin-sdk` first supplied the missing local
`dist/index.js` dependency. This avoided the Rust runner for the API smoke
test.

## Verified smoke test

- Private bind: `127.0.0.1:3100`
- `GET /api/health`: HTTP 200, `status: ok`, `authReady: true`, embedded
  PostgreSQL ready, startup recovery ready.
- `GET /api/companies`: HTTP 200 with `[]` (no fabricated company or agent).
- UI was API-only because the UI distribution was not built.

## UI verification

- `corepack pnpm --filter @paperclipai/ui build`: passed Vite production build
  (with upstream CSS pseudo-element and chunk-size warnings).
- With the server restarted, `GET /` returned HTTP 200, 9,448 bytes, and the
  document title `Paperclip`; `GET /api/health` returned HTTP 200.
- The service was stopped after the smoke test; no persistent process was left
  running.

## Deliberate limitations

- No Paperclip agent JWT/onboarding has been performed.
- No Paperclip company, task, or heartbeat is claimed as connected.
- The process was stopped after the smoke test to protect Mac responsiveness.
- Durable SSD-backed service data and launchd startup remain pending until the
  external SSD is mounted and its exact volume identity is confirmed.
