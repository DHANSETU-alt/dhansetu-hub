# Shakthi Jarvis Command Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the first working Jarvis slice: a shared, auditable personal command plane for goals, tasks, reminders, and routines, usable by voice and dashboard clients.

**Architecture:** Add a focused SQLite-backed personal command service rather than extending unrelated agent tables. Expose deterministic REST endpoints and a voice intent adapter; keep speaker verification and proactive scheduling behind explicit interfaces for later slices.

**Tech Stack:** Python 3.14, FastAPI, SQLite, existing orchestrator DB/config patterns, pytest/unittest-compatible tests, Next.js dashboard only after the API contract is stable.

**Spec:** `docs/superpowers/specs/2026-09-29-shakthi-jarvis-design.md`

## Global Constraints

- Shakthi remains local-first and auditable.
- Ambiguous requests must clarify rather than guess.
- Risky actions fail closed and require confirmation.
- Existing uncommitted work must be preserved.
- Voice recordings and profiles remain local by default and stay out of ordinary logs.

## Review Focus

- Duplicate reminder creation: repeated request identifiers must be idempotent.
- Time ambiguity: missing timezone or invalid recurrence must return a clear validation error.
- Authorization: Family and Guest roles must not create Owner-only objects or execute risky actions.
- Database failure: API must return a controlled error without partial writes.
- Natural-language ambiguity: unsupported voice phrases must produce clarification, not an invented task.

### Task 1: Personal command-plane schema and repository

**Files:**
- Create: `orchestrator/personal_plane.py`
- Modify: `orchestrator/db.py`
- Modify: `db/schema.sql`
- Create: `tests/test_personal_plane.py`

**Interfaces:**
- Produces `create_goal()`, `list_goals()`, `create_task()`, `list_tasks()`, `complete_task()`, `create_reminder()`, `list_due_reminders()`.
- Each write accepts `actor_id`, `actor_role`, and optional `request_id`; returns a JSON-serializable dict with `id`, timestamps, status, and audit reference.

- [ ] Write tests for goal creation/listing, task completion, reminder due filtering, idempotent `request_id`, role enforcement, and rollback on failed writes.
- [ ] Run `python -m pytest tests/test_personal_plane.py -q`; confirm expected failures identify missing repository functions/schema.
- [ ] Add focused tables for `personal_goals`, `personal_tasks`, `personal_reminders`, and `personal_audit_events` with indexes on owner/status/due time/request ID.
- [ ] Implement transaction-scoped repository methods using the existing SQLite connection/configuration conventions; never interpolate user-controlled SQL.
- [ ] Implement deterministic validation for required titles, ISO timestamps, supported roles, status transitions, and recurrence values.
- [ ] Run the focused tests and then the existing database-related tests.
- [ ] Commit with `git add orchestrator/personal_plane.py orchestrator/db.py db/schema.sql tests/test_personal_plane.py && git commit -m "feat: add personal command plane storage"`.

### Task 2: FastAPI command-plane endpoints

**Files:**
- Modify: `orchestrator/api.py`
- Create: `tests/test_personal_plane_api.py`

**Interfaces:**
- `POST /api/personal/goals`
- `GET /api/personal/goals`
- `POST /api/personal/tasks`
- `GET /api/personal/tasks`
- `POST /api/personal/tasks/{task_id}/complete`
- `POST /api/personal/reminders`
- `GET /api/personal/reminders/due`

- [ ] Write API tests for valid creation, validation failures, filtering, completion, duplicate request IDs, and role restrictions.
- [ ] Run the focused API tests and confirm they fail before implementation.
- [ ] Add Pydantic request/response models and route handlers that call only `personal_plane.py`; do not duplicate persistence logic in routes.
- [ ] Return stable HTTP semantics: 201 for creation, 200 for reads/actions, 400 for invalid input, 403 for role denial, and 503 for unavailable storage.
- [ ] Add request correlation IDs to response headers and audit records without storing raw audio or secrets.
- [ ] Run focused API tests and existing API tests.
- [ ] Commit with `git add orchestrator/api.py tests/test_personal_plane_api.py && git commit -m "feat: expose personal command plane API"`.

### Task 3: Voice intent adapter

**Files:**
- Modify: `orchestrator/voice.py`
- Modify: `orchestrator/jarvis_mediator.py`
- Create: `tests/test_personal_voice_commands.py`

**Interfaces:**
- `voice.detect_personal_intent(text) -> dict` with `action`, `entities`, `needs_clarification`.
- `jarvis_mediator.handle_personal_command(text, actor_id, actor_role) -> dict`.

- [ ] Write tests for English, Hindi/Gujarati mixed phrases, create-task, create-reminder, list-today, complete-task, and unsupported/ambiguous phrases.
- [ ] Run focused tests and confirm unsupported phrases fail safely.
- [ ] Implement a small deterministic parser that extracts title, relative date/time, and action; route uncertain inputs to clarification.
- [ ] Connect the adapter to the command-plane repository and preserve existing voice actions/tests.
- [ ] Ensure every mutation carries actor identity and request correlation data.
- [ ] Run focused voice tests plus the existing voice/Jarvis tests.
- [ ] Commit with `git add orchestrator/voice.py orchestrator/jarvis_mediator.py tests/test_personal_voice_commands.py && git commit -m "feat: add voice personal commands"`.

### Task 4: Founder command-center dashboard

**Files:**
- Create: `dashboard/app/personal/page.tsx`
- Modify: `dashboard/components/Sidebar.tsx`
- Modify: `dashboard/lib/api.ts`
- Create: `tests/test_personal_dashboard_contract.py` or an existing frontend test location if established by the project

- [ ] Add API client functions for goals, tasks, completion, and due reminders.
- [ ] Add dashboard tests or a build contract covering loading, empty, error, and successful states.
- [ ] Build a single “Today” view with overdue tasks, due reminders, active goals, and quick completion.
- [ ] Keep mutations explicit; no automatic destructive action from page load.
- [ ] Run the project’s frontend lint/build checks and manually verify the page against the local API.
- [ ] Commit with `git add dashboard/app/personal dashboard/components/Sidebar.tsx dashboard/lib/api.ts && git commit -m "feat: add personal command center"`.

### Task 5: Proactive reminder loop

**Files:**
- Create: `orchestrator/personal_scheduler.py`
- Modify: `orchestrator/watchdog.py`
- Create: `tests/test_personal_scheduler.py`

- [ ] Test due selection, quiet hours, deduplication, and failed notification handling.
- [ ] Implement a polling-safe scheduler that emits notification events but does not execute risky actions.
- [ ] Reuse existing alert/voice output interfaces and record delivery status in `personal_audit_events`.
- [ ] Add explicit enable/disable configuration and safe defaults.
- [ ] Run scheduler tests and the full available test suite.
- [ ] Commit with `git add orchestrator/personal_scheduler.py orchestrator/watchdog.py tests/test_personal_scheduler.py && git commit -m "feat: add proactive personal reminders"`.

## Execution order

Tasks 1–3 are the first deliverable. Task 4 follows the stable API contract. Task 5 follows once reminder persistence and voice responses are proven. Speaker enrollment/verification is a separate follow-up plan because it requires model and privacy decisions beyond this first slice.

## Self-review

The plan covers the spec’s command plane, voice interaction, audit/safety boundaries, proactive reminders, and dashboard. Speaker identity is intentionally excluded from this first implementation slice and remains a separately testable subsystem; no code should claim voice identity until that subsystem is implemented and live-verified.
