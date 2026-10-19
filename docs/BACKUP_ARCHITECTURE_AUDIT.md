# SHAKTHI_OS — Backup Architecture Audit

Phase 0 of the "3×3 Resilience + Safe Merge Architecture" plan. Real inspection only — no backup/merge system built yet, per the plan's own Section 28 rule ("do NOT immediately start copying the whole OS, first inspect").

Audit date: 2026-09-03. Evidence gathered directly from this machine and the founder's Google Drive — nothing below is assumed.

## LOCAL BACKUP

- One real tarball snapshot exists: `~/shakthi_os_backup_20260903.tar.gz` (1.8 MB, created earlier today), excludes `dashboard/node_modules` and `dashboard/.next` (matches the exclusion logic already documented in `BACKUP_CHECKLIST.md`).
- No generation rotation (G1/G2/G3) exists — this is a single, one-off snapshot, not a maintained lane.
- `BACKUP_CHECKLIST.md` (repo root) is a real, detailed manual checklist from 2026-08-23 — useful as a reference for what to include/exclude, but stale: it describes `shakthi.db` at 236 KB and "1 commit as of this backup." `shakthi.db` is now 3.1 MB and the repo has 4 commits with a huge uncommitted working tree on top (see below). The checklist itself has not been re-run since.
- No automated backup trigger of any kind exists in code — every grep hit for "backup" in `orchestrator/*.py` is unrelated (incident owner failover naming, `bug_fixer.py`'s per-patch `.backup` file before a code edit). There is no real snapshot-before-major-change mechanism.

## EXT SSD

**None exists.** The only non-system volume visible under `/Volumes` is "mantosh hd" — confirmed via `diskutil info` to be `Device Location: Internal`, `Protocol: PCI-Express` — this is the Mac's own internal drive, not an external SSD. Backup B, as specified, has zero real infrastructure today.

## REMOTE

- **GitHub: no remote configured.** `git remote -v` in `/Users/apple/shakthi-os` returns nothing. There is no off-machine copy of this repository anywhere. This is the single biggest real gap in the entire plan — if this Mac's disk failed right now, the only recovery paths are the one local tarball and whatever's in Drive (see below), neither of which contains today's work.
- **Google Drive: real, but stale.** Two real backup folders exist: `SHAKTHI_OS backup (2026-08-30)` and `SHAKTHI_OS Client Success backup (2026-08-26)`. Both predate today entirely — none of today's session (Control Plane 3.1 wiring, Command Center, Website Health Watcher, Trading Journal, dhansetuhub.info rebuild, Upkeeper's new features) is backed up anywhere off this machine.

## CURRENT GIT STATE

- 4 commits total, most recent: `de91370 Checkpoint: Task/Project tracks, SHAKTHI_OS 3.1 Phase 1, Concept 3 redesign progress`. No tags, single branch (`main`).
- **Massive uncommitted working tree** — 9 modified files (`dashboard/app/initiatives/page.tsx`, `MissionControlFlow.tsx`, `Sidebar.tsx`, `lib/api.ts`, `db/schema.sql`, `orchestrator/api.py`, `cli.py`, `db.py`, `routing.py`) and 14+ untracked new files/directories (`shakthi/` package, `dashboard/app/command-center/`, `control-plane-31/`, `website-health/`, `orchestrator/website_health.py`, 4 new test files, `state/`). This represents effectively all of tonight's real work — Control Plane 3.1, Mission Control redesign, Founder Command Center, Website Health Watcher — sitting entirely uncommitted.

## DATABASES TO PROTECT

- `shakthi.db`: 3.1 MB, 58 tables. Holds all runtime state (missions, tasks, decisions, finance, security reports, initiatives/milestones, the new website-health and Command Center data). No export/migration tooling exists for it beyond the raw file copy the tarball already does.
- Upkeeper's separate local state (`~/.blackboxops-cleaner/history.db`) is a second, independent local DB the plan needs to account for if "protect all databases" is meant to extend beyond the core Shakthi_OS repo.

## MEMORY STORES

- Claude Code's own memory files at `~/.claude/projects/-Users-apple/memory/` (the `MEMORY.md` index + individual files) are a real, separate persistence layer not covered by any of the above. Not part of `shakthi.db`, not in the tarball, not in Drive's existing backup folders.

## SECRETS/CONFIG

- Confirmed by `BACKUP_CHECKLIST.md` and this session's own work: no `.env` file exists anywhere in this project; credentials (Telegram token/chat ID, etc.) are passed as CLI flags only, never written to disk — consistent with the "never store secrets in the backup" rule the new plan requires. Nothing to redact, because nothing is stored.

## RECOVERY GAPS (real, prioritized)

1. **No off-machine backup of today's work at all.** Highest-priority real gap — a single point of failure on this one Mac's disk.
2. **No External SSD lane exists** — Backup B is entirely unbuilt.
3. **No git remote** — no GitHub-based recovery path, no real version history beyond local commits.
4. **No generation rotation (G1/G2/G3) anywhere** — every existing backup (tarball, Drive folders) is a single unmanaged snapshot, not a maintained, rotated lane.
5. **"Linux remains primary source of truth" is aspirational, not real.** Per this session's own tracked Task 10, the physical Linux machine has not been acquired yet — the only real live node today is this Mac. The 3×3 plan's node-identity assumptions (Section 5) don't yet match reality and should be treated as a future-state design, not a current constraint.
6. **No automated backup triggers** — nothing fires before a major change, migration, or deployment today; every backup so far has been manually initiated.
