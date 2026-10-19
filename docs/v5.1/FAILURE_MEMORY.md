# SHAKTHI_OS v5.1 — Failure Memory

Date: 2026-09-13
Real backing: this document formalizes a rule of use on top of the
**already-real** system documented in full in
`docs/v3.4/FAILURE_MEMORY_AND_BUGFIX_SYSTEM.md`. It does not define a new
schema, a new JSON store, or a new table — that would create exactly the
"parallel system that silently drifts from the real DB" problem the v3.4
doc already warned against. Read that document for the real schema
(`bugs`, `bug_events`, `patches`, `failure_analyses`) and the field mapping
from the founder's originally-requested shape to the real columns.

## 1. The one new rule v5.1 adds: search before you fix

Before proposing or applying any fix — whether dispatched through the
agent pipeline (`bug_fixer.yaml`) or done directly by this session —
check whether the same symptom has already been seen:

- Agent-pipeline work: `SELECT * FROM bugs WHERE file_path = ? AND
  function_name = ? AND status IN ('verified','fix_applied')` before
  `bug_fixer.yaml` derives a new patch. If a match exists, reuse its
  `fix_recommendation`/`patch_path` rather than re-deriving one from
  scratch — this is what `occurrence_count`/`duplicate_of` already exist
  to support (see v3.4 doc); the gap this rule closes is making the check
  happen *before* analysis, not just recording the duplicate after.
- Direct session work (not agent-dispatched): check
  `data/failure-memory.json` (the real export of `bugs` JOIN
  `failure_analyses`) for the same file/symptom before writing a new fix.
  As of 2026-09-13 this file has **6 real entries** (regenerate via
  `scripts/export_failure_memory.py` — never hand-edit it, or it silently
  drifts from the real DB).

## 2. What counts as a FailureMemory entry (real field mapping, from v3.4 doc)

| Conceptual field | Real source |
|---|---|
| failure_id | `bugs.id` or `failure_analyses.id` |
| date | `created_at` |
| symptom | `bugs.description` / `failure_analyses.summary` |
| root_cause | `root_cause` (both tables) |
| failed_attempts | Not a dedicated column yet — recoverable from `bug_events` rows of type `regressed`/`recurred`; a small additive field would be needed for an explicit list, not yet built |
| working_fix | `bugs.fix_recommendation` + the `patches` row once `applied=1` |
| files_changed | `bugs.file_path` / `patches.target_file` |
| prevention_rule | `failure_analyses.preventive_action` |
| test/check | `bug_events` row of type `tests_run`/`verified` |

## 3. Real entries logged this session (direct-session fixes, not agent-dispatched)

These were NOT written into the `bugs`/`failure_analyses` tables (they
weren't dispatched through the agent pipeline) — they're logged in
`docs/v3.4/SHAKTHI_FIX_LOOP_LOG.md` in its own append-only format, which is
the correct place for direct-session fixes per that log's existing
convention. Listing them here for cross-reference, not duplication:

1. Resume AI free-prompt-leak (revenue leak: full paid prompt text
   rendered/shipped regardless of payment status) — root cause and fix in
   `SHAKTHI_FIX_LOOP_LOG.md`, commit `ee9a53d`, **prevention rule**: any
   page gating content behind payment must generate/fetch that content
   server-side, never compute it in a `"use client"` component where the
   full logic ships to every visitor's browser regardless of auth state.
2. Stale pricing text in `/terms`/`/refunds` after a tier redesign —
   **prevention rule**: legal-copy pages describing prices/plans must be
   updated in the same commit as the pricing logic change, not treated as
   a separate follow-up (they were caught by a live-site audit, not by
   the original pricing change itself).
3. ChatGPT Sites publish `403 Invalid or expired token` — not yet a
   resolved failure (open, founder-approval-gated: re-authenticate the
   Sites session). Logging the symptom now so a future session doesn't
   re-diagnose the same "is this transient?" question: **confirmed not
   transient** — a fresh token was rejected immediately on retry.

## 4. What this document explicitly does not claim

It does not claim a unified failure-memory export exists across both
agent-pipeline bugs and direct-session fixes — those remain two real,
separately-formatted logs today (`data/failure-memory.json` vs.
`SHAKTHI_FIX_LOOP_LOG.md`). Unifying them is a real future improvement,
not something already built.
