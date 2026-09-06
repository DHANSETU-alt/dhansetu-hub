# SHAKTHI_OS — Backup Architecture

Phase 1 of the "3×3 Resilience + Safe Merge Architecture" plan (see the
founder's original spec for the full 28-section design). Covers ONLY the
Local backup lane (Backup A) — the other two lanes and everything past
Section 9 are explicitly not built yet; see "Not started" below.

## What's real right now

**Local backup lane** (`orchestrator/backup_manager.py`), CLI-driven via
`python3 -m orchestrator.cli --local-backup-create "REASON"`:

- Three real, rotated generations (G1 = latest known-good, G2 = previous,
  G3 = older stable), stored outside the working tree at
  `~/SHAKTHI_BACKUPS/local/` (override with `SHAKTHI_BACKUP_ROOT`).
- A snapshot is promoted to a generation **only** if every real check
  passes: git state captured, the full test suite passes, a real
  `py_compile` check across `orchestrator/` and `shakthi/` passes, the
  API module actually imports and wires its real routes, the database
  passes `PRAGMA integrity_check`, and a real deterministic secret-scan
  (`security.scan_api_key_exposure()` — the closest existing equivalent
  to the spec's "Guardian" role; no literal Guardian agent exists yet)
  finds nothing. If any check fails, the snapshot is stored as
  `UNVERIFIED_SNAPSHOT` and never promoted — proven live during
  development: a deliberately broken test run correctly produced
  `UNVERIFIED_SNAPSHOT`, left G1 untouched, and a subsequent good run
  correctly rotated G1→G2.
- Every backup records real metadata (timestamp, git commit/branch/dirty
  count, SHAKTHI version, DB schema hash, test/build/security results,
  hostname, reason) plus a real SHA-256 of the tarball itself.
- `--local-backup-verify GEN` runs a real restore drill: recomputes the
  tarball's hash and compares it to what was recorded, confirms real
  `tar` integrity, and attempts a real extraction. Proven to actually
  detect corruption, not just report success — a byte-flip test on a
  real stored tarball correctly failed the hash check, the integrity
  check (real zlib decompression error), and the overall verdict.
- `--local-backup-list` shows all three generations plus any unverified
  snapshots.
- 8 real permanent unit tests in `tests/test_backup_manager.py` cover the
  tarball/rotation/relabel/verify mechanics against a temp directory
  (the full-suite-in-the-loop check itself was exercised live via the
  actual CLI during development, not inside the test suite — running the
  whole suite recursively from within a test would be slow and circular).

A real bug was caught and fixed during this build: generation rotation
(`shutil.move`) carries a directory's `metadata.json` as-is, so without
an explicit relabel step, a moved G1→G2 directory's own metadata still
said `"generation": "G1"` — `--local-backup-list` printed "G1" twice.
Fixed by rewriting the `generation` field at rotation time; regression
test added (`test_rotation_relabels_metadata_not_just_moves_files`).

## Not started (explicit, not implied)

- **External SSD lane (Backup B)** — no SSD is mounted on this machine
  (confirmed in `docs/BACKUP_ARCHITECTURE_AUDIT.md`). Zero code exists
  for this lane.
- **Remote lane (Backup C)** — blocked on the founder actually getting a
  copy off this machine first (no GitHub remote, Drive backups are
  stale). A real, separate blocker tracked outside this task.
- **Safe Merge Engine** (spec sections 10–18) — three-way merge, conflict
  classification, DB/memory/skill-aware merge, running-OS protection,
  rollback. Nothing built.
- **Disaster recovery levels R1–R5, restore drills as a scheduled
  process, backup health dashboard, multi-node merge view** (sections
  19–22). Nothing built.
- **Angella backup-supervisor gate, Guardian as a real agent, no-fork-
  chaos governance, explicit versioning policy, future-upgrade
  preservation** (sections 23–27). Nothing built — the "Guardian"
  concept used above is only the existing `security.py` secret scan, not
  a real standalone agent.
- **Automated backup triggers** (spec section 8: before major
  upgrade/migration/deployment/etc.) — `create_local_backup()` exists and
  works, but nothing calls it automatically yet. Every backup so far has
  been manually invoked.
