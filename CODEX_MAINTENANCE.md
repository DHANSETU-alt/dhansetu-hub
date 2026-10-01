# DhanSetu Hub Codex maintenance contract

This file is the operating contract for `/Users/apple/shakthi-os`.

## Scope and ownership

- Codex only. Do not invoke Claude Code, install Claude tooling, or create a
  replacement repository.
- Product scope: DhanSetu Hub and `dhansetuhub.in`.
- Host: the user's MacBook. Durable application state: the confirmed external
  SSD, never an unverified `/Volumes/...` path.
- Preserve `.git`, customer data, migrations, uploads, payment/auth records,
  backups, audit logs, and existing uncommitted work.

## Change discipline

- Inspect the current repository and Graft context before editing source.
- Make small reversible changes with tests and descriptive progress evidence.
- Never print secrets, reset passwords, bypass payment verification, or infer
  founder privileges from client input.
- Use honest status labels: actual, pending, estimated, stale, unavailable.
- Do not delete or quarantine legacy material until the encrypted SSD archive,
  manifest, sample restore, and seven-day retention requirements are satisfied.

## Runtime and rollback

- The SSD mount is a hard startup precondition. Missing storage must prevent
  service startup rather than writing to the Mac's internal disk.
- Use the documented host guard and production build; do not use the heavy
  development stack for hosting.
- Keep one documented startup, stop, backup, restore, database, and scheduler
  path. Every deployment must have a health check and rollback path.
- Hindsight and Paperclip are optional local support services until their
  endpoints, data locations, identities, and heartbeats are verified.

## Required verification

Before declaring work complete, run relevant tests, build checks, security
checks, service health checks, backup/restore checks, and browser smoke tests.
Report blocked founder-only actions separately and never fabricate live proof.
