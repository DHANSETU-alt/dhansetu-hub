# DhanSetu Mission Inventory

Inventory date: 2026-09-23 IST. Classifications are provisional until the external-SSD archive and restore test pass. Ambiguous material remains protected.

| Absolute path | Size | Git state | Purpose / dependencies | Modified | Classification |
|---|---:|---|---|---|---|
| `/Users/apple/shakthi-os` | 3.8 GB | `main`, HEAD `c788dbf`, remote `linux-3.2`, heavily dirty | Active Python orchestrator, Next.js dashboard, SQLite DB, tests, product code | 2026-09-23 17:54 IST | KEEP-DHANSETU |
| `/Users/apple/shakthi-os/shakthi.db` | 38,215,680 bytes | untracked/ignored runtime data | Current SQLite authority; 59 tables; integrity check `ok` | 2026-09-23 17:54 IST | KEEP-DHANSETU |
| `/Users/apple/shakthi-os/dashboard` | 3.0 GB | parent tracked + generated files | Next.js 16 dashboard, Node/npm, local API dependency on `:8787` | 2026-09-13 14:19 IST | KEEP-DHANSETU |
| `/Users/apple/shakthi-os/dhansetu-web` | 216 KB | nested clean `main`, HEAD `e7e0ce1`, GitHub `DHANSETU-alt/dhansetu-web` | Two static DhanSetu HTML pages to compare/migrate | 2026-09-11 20:46 IST | MIGRATE-INTO-DHANSETU |
| `/Users/apple/shakthi-os/data` | 12 KB | untracked | Failure-memory state; inspect before migration | 2026-09-13 02:49 IST | UNKNOWN-PROTECT |
| `/Users/apple/shakthi-os/pdf_studio_files` | pending | ignored runtime data | PDF Studio uploads/output | pending | KEEP-DHANSETU |
| `/Users/apple/shakthi-os/dashboard/node_modules` | included in dashboard size | generated | Rebuildable npm dependencies from lockfile | 2026-08-23 | GENERATED-SAFE-TO-REBUILD |
| `/Users/apple/shakthi-os/dashboard/.next` | generated | ignored | Rebuildable Next.js output | 2026-09-13 | GENERATED-SAFE-TO-REBUILD |
| `/Users/apple/shakthi-os/linux_backup_before_wipe_20260913` | 775 MB | untracked | Historical full OS backup; may contain unique data | 2026-09-13 14:04 IST | UNKNOWN-PROTECT |
| `/Users/apple/shakthi-os/blackboxops_os_backup` | pending | untracked/ignored | Historical generated/site backup | 2026-09-23 | UNKNOWN-PROTECT |
| `/Users/apple/shakthi-os/backups` | pending | mixed | Existing backups and working-board snapshots | pending | UNKNOWN-PROTECT |
| `/Users/apple/claude-code` | pending | clean upstream plus Graft config; origin `anthropics/claude-code` | Unrelated tooling repository, not DhanSetu source | 2026-09-23 | UNKNOWN-PROTECT |
| `/dev/disk2s1` | 240.1 GB | not applicable | External USB SSD; Linux partition; UUID `45494F70-F726-493F-AABA-30189410DB0C`; not mountable by macOS currently | not mounted | UNKNOWN-PROTECT |

## Active Runtime Inventory

- Local API `127.0.0.1:8787`: not responding; `.api.pid` is stale.
- Local dashboard `127.0.0.1:3000`: not responding; `.dashboard.pid` is stale.
- launchd label `com.shakthios.dashboard`: registered, last status observed as failed/non-running.
- User crontab: multiple Shakthi/Jarvis-era website, security, sentinel, customer-health, watchdog, DNS, founder-review, and live-watch jobs remain active.
- Several cron jobs embed a Telegram bot credential in command arguments. The credential is intentionally omitted here and must be rotated.

## Baseline Verification

- `python3 -m unittest discover tests`: 469 tests passed.
- `npm --prefix dashboard run lint`: failed, 17 errors and 3 warnings.
- `npm --prefix dashboard run build`: failed because `next/font` could not fetch Google Geist fonts.
- `git diff --check`: passed.
- SQLite `PRAGMA integrity_check`: `ok`.

## Cleanup Gate

No item is approved for quarantine or deletion yet. `LEGACY-OS`, `DUPLICATE`, and final generated-output classifications require content comparison, dependency/caller checks, a secret-free manifest, encrypted SSD archive, and sample restore first.

