# DhanSetu Hub mission status

Updated: 2026-09-26 IST

## Implemented and verified

- Canonical workspace identified: `/Users/apple/shakthi-os`.
- Nested DhanSetu repository identified: `/Users/apple/shakthi-os/dhansetu-web`.
- Existing dirty work protected; no reset, broad deletion, or replacement repo.
- Codex-only maintenance contract added in `AGENTS.md` and
  `CODEX_MAINTENANCE.md`.
- ECC installed as a native Codex plugin; support documented.
- Hindsight and Paperclip checkouts preserved under `/Users/apple/shakthi-services`.
- Paperclip SDK/server/UI builds and local API/UI smoke tests passed.
- Hindsight/Paperclip bounded health probes wired into Sentinel and Mission
  Control with explicit unavailable/configured states.
- Mission Control renders from the real orchestrator API with neon flow,
  30-second refresh, and separate support-service badges.
- Dashboard Webpack production build passed; root and Mission Control smoke
  tests passed.
- 484 canonical Python tests passed.
- SSD-guarded host, health, stop, API, Paperclip, and launchd templates added;
  plist and shell validation passed.
- Mac performance report/relief tooling added after diagnosing the Paperclip
  Rust build and one-second dashboard refresh storm.

## Not live / blocked by external state

- The external SSD has now been erased on the verified `/dev/disk2` target and
  mounted as `/Volumes/DhanSetuSSD` using case-sensitive APFS. It is currently
  unencrypted because the owner-only passphrase prompt was stopped; no durable
  application data has been written yet.
- Hindsight has no configured LLM provider/local model or SSD-backed database
  path; retain/recall is not claimed live.
- Paperclip onboarding has not created a company, JWT, agents, or heartbeats.
- `dhansetuhub.in` production traffic has not been switched to this Mac.
- Google sign-in, live Razorpay, external TLS/tunnel, and owner-only content or
  social integrations remain unverified.
- Existing crontab contains multiple legacy schedulers and inline Telegram
  credentials. No crontab mutation was made; token rotation is required.

## Founder-only actions

1. Encrypt `/Volumes/DhanSetuSSD` locally with a founder-held passphrase.
2. Rotate the exposed Telegram bot token through the owner/admin flow.
3. Create `/Users/apple/.config/dhansetu/host.env` with the confirmed SSD path.
4. Supply/authorize the Hindsight provider or local model configuration.
5. Approve Paperclip onboarding and DhanSetu agent identities.
6. Approve DNS/HTTPS cutover only after backup, restore, and rollback gates pass.
