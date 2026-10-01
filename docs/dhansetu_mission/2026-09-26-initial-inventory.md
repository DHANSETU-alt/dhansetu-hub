# Initial DhanSetu Mission Inventory — 2026-09-26

## Canonical scope candidate

- Parent workspace: `/Users/apple/shakthi-os`
- Parent Git remote: `blackboxops@100.86.74.97:ShakthiOS_v3.2`
- Parent branch: `main`
- Parent HEAD: `c788dbf`
- Parent state: heavily dirty; existing user changes are protected and have not
  been overwritten or cleaned.
- Nested DhanSetu repository: `/Users/apple/shakthi-os/dhansetu-web`
- Nested remote: `https://github.com/DHANSETU-alt/dhansetu-web.git`
- Nested branch: `main`
- Nested HEAD: `e7e0ce1`
- Nested state at inspection: clean.

## Initial classification

| Path | Classification | Evidence / handling |
|---|---|---|
| `/Users/apple/shakthi-os/dhansetu-web` | KEEP-DHANSETU | Dedicated DhanSetu repository, clean Git state, domain references. |
| `/Users/apple/shakthi-os/dashboard` | MIGRATE-INTO-DHANSETU | Existing founder dashboard and payment/auth operational code; preserve until mapped and tested. |
| `/Users/apple/shakthi-os/orchestrator` | MIGRATE-INTO-DHANSETU | Existing API, scheduler, payment, and automation code; preserve until mapped and tested. |
| `/Users/apple/shakthi-os/db` | KEEP-DHANSETU | Database schema and payment records are protected. |
| `/Users/apple/shakthi-os/state` | UNKNOWN-PROTECT | Contains SQLite state databases; no deletion or migration yet. |
| `/Users/apple/shakthi-os/data` | UNKNOWN-PROTECT | Data directory exists; contents and ownership require a targeted audit. |
| `/Users/apple/shakthi-os/linux_backup_before_wipe_20260913` | UNKNOWN-PROTECT | Explicitly protected until archive/restore scope is verified. |
| `/Users/apple/shakthi-services/hindsight` | SUPPORT-SERVICE | Fresh clone of requested Hindsight repository; separate from app source. |
| `/Users/apple/shakthi-services/paperclip` | SUPPORT-SERVICE | Fresh clone of requested Paperclip repository; separate from app source. |

## Current blockers

- No external SSD is mounted under `/Volumes`; no archive, quarantine, or
  durable application state may be written there yet.
- No Docker executable is available.
- No Hindsight LLM provider credential or local LLM endpoint is configured.
- The parent Shakthi OS repository has extensive uncommitted changes; cleanup
  cannot safely begin until a protected inventory and archive target exist.
- Read-only `diskutil list` confirms only the internal 1 TB APFS container is
  present; no external physical disk is currently attached or mounted.

## Actions taken

- Cloned Hindsight and Paperclip into `/Users/apple/shakthi-services`.
- Began installing Paperclip dependencies; no application source was modified.
- Did not delete, move, reset, or overwrite any existing project material.

## Storage guard

`scripts/dhansetu-host.sh` now requires an explicitly confirmed
`DHANSETU_SSD_ROOT`, rejects internal storage, verifies the mount with `df`,
and refuses startup when the path is absent. A no-variable smoke test returned
the expected safe refusal. No volume was formatted or modified.
