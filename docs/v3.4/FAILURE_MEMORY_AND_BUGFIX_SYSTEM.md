# Failure Memory & Bugfix System — v3.4

Date: 2026-09-13
Evidence: every schema fragment below was read directly from
`db/schema.sql` this session (not paraphrased from memory) and cross-checked
against `dashboard/app/bugs/page.tsx`.

## 0. Real state: this system already exists

The founder's request describes a failure-memory system with: failure_id,
date, agent, task_id, symptom, root_cause, fix_applied, files_changed,
prevention_rule, regression_check, status. **Three real tables already
cover essentially all of this** — `bugs`, `bug_events`, `patches` — plus a
fourth, `failure_analyses`, that is even closer to the requested shape
(it has an explicit `preventive_action` field and a 5-Whys record). Do not
build a new parallel schema. Extend these.

### `bugs` (real, `db/schema.sql`)

```sql
CREATE TABLE IF NOT EXISTS bugs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  severity TEXT NOT NULL DEFAULT 'P2',        -- P0 Critical .. P4 Trivial
  status TEXT NOT NULL DEFAULT 'open',        -- open|analyzing|patch_proposed|
                                               -- ceo_approved|ceo_rejected|fix_applied|
                                               -- verified|regressed|closed
  source TEXT NOT NULL DEFAULT 'manual',      -- manual|test_failure|task_failure|error_log
  file_path TEXT, function_name TEXT, module_name TEXT, line_number INTEGER,
  root_cause TEXT,
  fix_recommendation TEXT,
  confidence INTEGER,                         -- 0-100
  related_task_id INTEGER REFERENCES tasks(id),
  related_error_id INTEGER REFERENCES error_log(id),
  patch_path TEXT,
  current_patch_id INTEGER,                   -- -> patches(id)
  applied_at TEXT,
  occurrence_count INTEGER NOT NULL DEFAULT 1,   -- real recurrence counter
  duplicate_of INTEGER REFERENCES bugs(id),      -- real "this is a repeat" link
  regression_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

`occurrence_count`/`duplicate_of` are populated by real code
(`bug_fixer._check_recurrence()`, per the repo) — **"no repeated bugs" is
not aspirational, it already runs.**

### `bug_events` (real) — the append-only lifecycle trail

`event_type`: `detected → analyzed → patch_proposed → qa_reviewed →
security_reviewed → ceo_approved/ceo_rejected → patch_applied →
tests_run → verified → regressed → recurred`. This is the "what failed,
why, where, next action" trail in practice — each event's `payload`
carries the detail for that step.

### `patches` (real) — rollback-safe by construction

```sql
CREATE TABLE IF NOT EXISTS patches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bug_id INTEGER NOT NULL REFERENCES bugs(id),
  target_file TEXT NOT NULL,
  full_file_path TEXT NOT NULL,   -- staged, never the live file
  diff_path TEXT,
  applied INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

A fix is never live until `applied=1` — this already is the rollback
mechanism the founder's plan asks for.

### `failure_analyses` (real) — closest match to the founder's exact ask

```sql
CREATE TABLE IF NOT EXISTS failure_analyses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_type TEXT NOT NULL,       -- bug|task_failure|incident|manual
  source_id INTEGER,
  title TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'P2',
  summary TEXT NOT NULL,
  five_whys TEXT NOT NULL,         -- JSON array, why #1 -> #5
  root_cause TEXT NOT NULL,
  corrective_action TEXT NOT NULL, -- what was actually done
  preventive_action TEXT NOT NULL, -- the poka-yoke — this IS "prevention_rule"
  lessons_learned TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',   -- open|closed
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

Per the schema's own comment, this was deliberately scoped down from a
larger Six Sigma/DMAIC proposal to "one high-leverage process... not the
whole framework at once" — a real, prior CEO decision. Keep that scoping;
don't re-expand it as part of this plan.

### Field mapping (founder's ask → real column)

| Founder's field | Real source |
|---|---|
| failure_id | `bugs.id` or `failure_analyses.id` |
| date | `created_at` on either table |
| agent | not a direct column today — recommend adding `agent_id` to `failure_analyses` (small additive migration) |
| task_id | `bugs.related_task_id` |
| symptom | `bugs.description` / `failure_analyses.summary` |
| root_cause | `root_cause` on both tables |
| fix_applied | `bugs.fix_recommendation` + `patches` row once `applied=1` |
| files_changed | `bugs.file_path`/`patches.target_file` |
| prevention_rule | `failure_analyses.preventive_action` |
| regression_check | `bugs.regression_count` + a `bug_events` row of type `regressed` |
| status | `bugs.status` / `failure_analyses.status` |

## 1. Real gap: `data/failure-memory.json`

This file does not exist. **Recommendation: it should be a generated
export, not a hand-authored parallel store** — a small script
(`scripts/export_failure_memory.py`, new, low-risk) that queries `bugs`
JOIN `failure_analyses` (via `source_id` where `source_type='bug'`) and
writes the JSON. Regenerate it on demand or via the existing cron, never
edit it by hand — otherwise it silently drifts from the real DB and
becomes exactly the kind of "fake status" the founder's rules forbid.

## 2. Before fixing a new bug: search failure memory first

Concrete, buildable today: before `bug_fixer.yaml` or `kaixen_bot.yaml`
proposes a new patch, query
`SELECT * FROM bugs WHERE file_path = ? AND function_name = ? AND status IN ('verified','fix_applied')`
first. If a match exists, reuse its `fix_recommendation`/`patch_path`
instead of re-deriving one — this is what `occurrence_count`/
`duplicate_of` already exist to support; the missing piece is just making
the *check* happen before analysis starts, not after.

## 3. Live dashboard

`dashboard/app/bugs/page.tsx` — real, queries `getBugs()` → `/api/bugs`,
shows Open / P0-P1 Critical / Verified Fixed / Regressed tiles. Its own
subtitle already states the real pipeline: "analyze → propose (staged,
never live) → QA → Security → CEO → apply → verify." `dashboard/app/
failure-analyses/page.tsx` exists with the same real backing pattern.
No new dashboard page is needed for failure memory — extend these two.
