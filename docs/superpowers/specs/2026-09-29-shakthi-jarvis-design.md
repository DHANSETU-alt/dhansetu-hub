# Shakthi OS Jarvis Upgrade Design

**Date:** 2026-09-29  
**Status:** Draft for founder review  
**Scope:** Shakthi OS product architecture; no host-OS migration

## Product intent

Shakthi OS will become a voice-first personal operating layer: it should
recognize the founder and household speakers, understand natural requests,
maintain tasks/goals/reminders/memory, proactively surface important events,
and safely execute approved actions across the existing agent system.

The experience should feel like a capable personal operator, while remaining
local-first, permissioned, explainable, and auditable.

## Existing foundation

The repository already contains voice intent routing and speech output,
Sentinel monitoring, agent routing, task/event storage, dashboard pages, audit
logging, and a Jarvis mediator test surface. The upgrade should extend those
capabilities through shared domain services instead of creating parallel
task, voice, or alert implementations.

## Core architecture

### 1. Voice interaction plane

`Wake word -> audio capture -> speaker verification -> transcription -> intent
resolution -> policy check -> action/query -> response speech -> audit event`

Speaker profiles have an identity, role, enrollment metadata, confidence
threshold, and allowed capabilities. Roles are Owner, Family, and Guest. A
low-confidence or unknown speaker receives a safe response and cannot invoke
risky actions.

The first implementation will preserve the existing local transcription and
macOS speech output paths behind interfaces so platform-specific audio can be
replaced without changing command handling.

### 2. Personal command plane

One service owns the shared objects used by voice, dashboard, and automation:

`Goal -> Project -> Task -> Reminder -> Routine -> Outcome`

Objects support ownership, priority, status, due dates, recurrence, tags,
source, created/updated timestamps, and audit history. Natural-language input
may create or update objects only after deterministic parsing and policy
validation. Ambiguous requests produce a clarification rather than a guess.

### 3. Context and memory

The command plane supplies bounded context: current speaker, time, upcoming
reminders, active goals, recent conversation, system health, and relevant
stored knowledge. Context is selected by intent and never injects unrelated
memory into a task.

### 4. Proactive routine engine

A scheduler evaluates due reminders, recurring routines, Sentinel incidents,
calendar events, and stale goals. Notifications are deduplicated and have a
quiet-hours policy. Low-risk informational events may be spoken automatically;
actions that change data, spend money, send messages, or affect external
systems require explicit confirmation.

### 5. Safety and audit

Every command records speaker identity/confidence, interpreted intent,
permission decision, tools invoked, result, and response. Risky operations
fail closed when identity, policy, or required integration state is missing.

## Delivery slices

1. **Command-plane foundation:** schema/service for goals, tasks, reminders,
   routines, and audit events; REST endpoints and tests.
2. **Voice-first personal assistant:** natural commands for creating,
   listing, completing, postponing, and querying personal objects.
3. **Speaker identity:** enrollment, local voice-profile storage, confidence
   gating, role permissions, and unknown-speaker behavior.
4. **Proactive Jarvis loop:** scheduler, spoken notifications, quiet hours,
   deduplication, and Sentinel/reminder integration.
5. **Founder command center:** dashboard views for today, goals, routines,
   reminders, voice history, and pending approvals.
6. **Hardening:** backup/restore coverage, failure recovery, latency metrics,
   privacy controls, and live microphone verification.

## Safety boundaries

- No autonomous purchases, deletions, credential changes, deployments, or
  external messages without confirmation.
- Speaker recognition authorizes capability but does not replace action-level
  policy checks.
- Voice recordings and profiles remain local by default and are excluded from
  ordinary logs.
- Existing uncommitted work is preserved; implementation must be incremental
  and tested against the current tree.

## Success criteria

- The founder can say: “Shakthi, remind me tomorrow at 9 to review revenue” and
  receive a confirmation with the created reminder.
- The founder can ask for today’s priorities, active goals, system health, and
  overdue work in natural language.
- A family speaker can use permitted personal features but cannot invoke
  owner-only operations.
- Shakthi proactively announces configured reminders and critical incidents,
  respecting quiet hours and deduplicating repeated alerts.
- Every command is inspectable in the audit trail and all existing tests remain
  green.
