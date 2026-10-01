# SHAKTHI_OS v3.3 — Architecture, Gap Report, Migration Order

Companion to `PHASE0_AUDIT.md` — read that first. Everything in the gap
table below is anchored to a real file/table cited there, not a guess.

## Gap report

| Capability | Current state (real, cited) | v3.3 target | Gap | Risk if skipped | Priority |
|---|---|---|---|---|---|
| Task model | `tasks` table, flat, 3-state status | Persistent DAG with dependencies, checkpoints, leases | No dependency edges at all — every "parallel" claim today is actually sequential or manually coordinated | Cannot safely parallelize without this; false "parallel execution" claims | **P0 — Phase 2** |
| Worker model | `workers` table, thin, no lease/heartbeat | Durable actor: lease, heartbeat, mailbox, resource_budget, status enum from item 3 | A worker marked "busy" with a dead process looks identical to one still working | Silent stuck work, no automatic recovery | **P0 — Phase 3** |
| Event system | `task_events`, minimal fields | Canonical Event (item 38): correlation_id, worker, node, severity, evidence_refs | Can't trace one founder command end-to-end across subsystems today | No real distributed tracing (item 97) is possible until this exists | **P1 — Phase 2/3** |
| Policy engine | `access.py`, single `allowed()` boolean | ALLOW/DENY/REQUIRE_APPROVAL/SANDBOX_ONLY/ALLOW_WITH_LIMIT | Every decision today is binary; no approval queue, no sandbox-only tier | Cannot safely grant AUTO mode (item 21) without this existing first | **P0 — Phase 4** |
| Secret handling | Not located this pass — flag for Phase 1 deep-read of `config.py` | Secret Broker, never in prompt/logs | Unknown exposure surface until confirmed | Could already be leaking secrets into model context — **verify before building anything else** | **P0 — Phase 1, before Phase 4** |
| Model gateway | `model_gateway.py`, real, 2 providers (Ollama, Claude) | AgentGateway: N providers, capabilities/cost/latency/health, routing on evidence | No Codex/OpenAI provider confirmed; no adaptive routing, `default_model_tier` is static per-agent config | Cannot honestly claim "multi-model" today | **P1 — Phase 5** |
| Angella | `pa_angella.py`, real, prompt-refine + 1-hop routing | Mission Compiler → DAG → resource plan → verification → lessons | Angella today does step 1 of a 12-step pipeline | This is the single biggest gap between what's claimed ("orchestrates missions") and what's real | **P0 — Phase 1 (spec), Phase 6/7 (build)** |
| Guardian | Does not exist | Independent supervisory control, cannot be overridden by task prompts | From-scratch build | No independent check on agent behavior exists today at all | **P1 — Phase 10** |
| Sentinel | `sentinel.py`, real, 329 lines, scope unconfirmed | Watch agents/daemons/automations/DB/queues/models/storage/nodes/backups | Unknown until Phase 1 reads the file in full | Possible false confidence that "monitoring exists" when scope is narrower | **P1 — Phase 1 read, then Phase 10** |
| Incident pipeline | `incidents`/`incident_events`, genuinely mature | DETECT→CLASSIFY→EVIDENCE→REPRODUCE→ROOT CAUSE→PLAN A/B/C→ESCALATE | **Smallest gap of anything audited.** Already has the right status lifecycle | Low — this is closest to done | **P2 — extend, don't rebuild** |
| Service supervision | Foreground processes only, no systemd/launchd | Supervised core scheduler/Guardian/Sentinel services | A crashed terminal kills the whole system silently | Directly causes item 103's restart-recovery failure mode today | **P1 — Phase 11** |
| Backup / resilience | Real 1-generation snapshot precedent (`VERSION.txt`), no automation, SSD not connected | 3×3 fabric, verified restore drills | No automated backup exists; SSD leg physically blocked tonight | Real data-loss exposure until this exists | **P0 — Phase 12, start manual backup now** |
| Software/App/Automation Factories | Do not exist | Full pipelines per items 25/26/32 | From-scratch build, largest scope item in the entire spec | This is 6+ months of work by itself | **P3 — Phase 6-8, after kernel is real** |

## Proposed core architecture (incremental, not a rewrite)

Keep everything in the gap report marked "extend, don't rebuild." The
existing `tasks`/`task_events`/`workers`/`work_queue`/`incidents` tables
are real and working — v3.3's job is to **add** columns and **new**
tables around them, not replace them:

1. **`tasks` → gains `parent_task_id`, `mission_id`, `depends_on` (JSON
   array of task_ids), `checkpoint` (JSON), `lease_owner`, `lease_expires_at`.**
   This turns the existing flat list into a real DAG with the smallest
   possible schema change — no new table needed for the DAG itself, just
   self-referencing edges on the table that already exists.
2. **New `missions` table** — one row per founder command, holding the
   MissionSpec fields from item 6 (objective, acceptance_criteria,
   constraints, budget, deadline, verification_plan, rollback_plan).
   `tasks.mission_id` references it.
3. **New `events` table** (the Canonical Event, item 38) — replaces
   `task_events` going forward; keep `task_events` read-only for history,
   write new events to `events` with the full correlation_id/worker/node/
   severity/evidence_refs shape.
4. **`workers` → gains `lease_expires_at`, `heartbeat_at`,
   `resource_budget` (JSON), `capabilities` (JSON)**. A worker is not
   "alive" unless `heartbeat_at` is within a defined freshness window —
   enforce this as a real check, not a status field anyone can leave stale.
5. **New `policy_decisions` table + `orchestrator/policy.py`** — every
   `access.allowed()` call site gets replaced with a call into this new
   module, which returns one of the 5 decision types (item 20) and logs
   the decision with its inputs. `access.py`'s existing binary check
   becomes the `ALLOW`/`DENY` special case of the new 5-way decision, so
   nothing that currently works breaks.
6. **Secret Broker**: before any of the above, Phase 1 must confirm
   exactly how `ANTHROPIC_API_KEY` and any other credential reach
   `model_gateway.py` today (env var read directly? `.env` file?). If
   found to be read directly into a variable that could reach a prompt or
   log, that is the first real fix — before any new feature work.

## Dependency graph (what blocks what)

```
Phase 0 Audit (this doc)
   │
   ▼
Phase 1: Secret audit + typed contracts + pytest baseline
   │
   ├──▶ Phase 2: tasks/missions/events schema migration (DAG)
   │        │
   │        ▼
   │    Phase 3: workers lease/heartbeat + real work-stealing
   │        │
   │        ▼
   │    Phase 4: policy.py (5-way decisions) ──▶ Phase 21: Founder AUTO mode
   │
   ├──▶ Phase 5: AgentGateway (extend model_gateway.py, add Codex/OpenAI)
   │        │
   │        ▼
   │    Phase 6: Automation Factory (needs DAG + policy + gateway)
   │        │
   │        ▼
   │    Phase 7: Software Factory (needs workspace isolation, Phase 24)
   │        │
   │        ▼
   │    Phase 8: Application Factory (needs Software Factory)
   │
   └──▶ Phase 10: Guardian + Sentinel v3 (needs events table from Phase 2)
            │
            ▼
        Phase 11: Service supervision + restart recovery
            │
            ▼
        Phase 12: 3×3 resilience fabric
```

Phases 5, 10 can run in parallel with 2/3/4 — they don't depend on the
DAG existing. Phases 6/7/8 are strictly sequential and are each large
enough to be their own multi-week effort; do not start Phase 7 before
Phase 6 has a real, verified pilot per item 122.

## First 7-day implementation sprint

Day 1: Run the real `pytest` suite (43 files), read `config.py` for the
       secret-handling answer Phase 1 needs, read `sentinel.py` and
       `routing.py` in full (both flagged unread in the audit).
Day 2: Add `parent_task_id`/`mission_id`/`depends_on`/`checkpoint`/
       `lease_owner`/`lease_expires_at` columns to `tasks` (migration,
       not a rewrite — `CREATE TABLE IF NOT EXISTS` won't add columns,
       so this needs the same `ALTER TABLE` pattern already used for
       `agents.squad`, per the comment in `db/schema.sql`).
Day 3: Create the `missions` table + a minimal `orchestrator/missions.py`
       with `create_mission(objective, ...) -> mission_id`. No LLM
       involvement yet — this is deterministic plumbing (item 93).
Day 4: Create the `events` table + `orchestrator/events.py` with
       `record_event(...)`. Wire it into `routing.run_task` as an
       additive call (existing `task_events` writes stay untouched).
Day 5: Add `heartbeat_at`/`lease_expires_at` to `workers`, plus a
       `is_worker_alive(worker_id)` function with a real freshness
       check. No behavior change to existing dispatch yet — just make
       liveness queryable.
Day 6: Write `orchestrator/policy.py` with the 5-way decision type,
       backed initially by the exact same rules `access.allowed()`
       already encodes (so nothing regresses), with `policy_decisions`
       logging every call.
Day 7: Wire one real end-to-end path — the first automation pilot below
       — through the new `missions`/`events`/`policy` plumbing, and run
       the v3.3 release-criteria vertical slice checklist (item 122)
       against it.

## First automation pilot (item 123)

CSV watch-folder pipeline, exactly as the founder's spec proposes:
`WATCH → VALIDATE → PROCESS → WRITE CLEAN OUTPUT → QUARANTINE INVALID →
REPORT → RECORD EVENTS`. Chosen because it needs zero cloud dependency,
is trivially idempotent (same file in = same result), and exercises the
new `missions`/`events`/`policy` plumbing without touching anything
customer-facing or payment-related.

## First software pilot (item 124)

"SHAKTHI Task Inspector" — a small local-only Linux CLI/TUI that reads
the real `tasks`/`missions`/`workers` tables directly (no new API layer
needed yet) and lets the founder search/filter tasks, see mission
details, worker heartbeat state, and event history. Deliberately boring
and internal-only — proves the Task DAG + events + worker-liveness work
Phase 1-3 built, without any Software Factory pipeline existing yet
(that pipeline is Phase 7, much later).

## What this document deliberately does not do

It does not write any Execution Kernel code, does not touch
`access.py`/`model_gateway.py`/`pa_angella.py` yet, and does not start
Phase 1. Per the founder's own instruction ("WAIT only if a
destructive/high-risk decision genuinely requires Founder approval") —
none of Phase 1's first three actions (run pytest, read two existing
files, read `config.py` for the secret question) are destructive, so
Phase 1 begins immediately after this document exists. Anything past
that — the first schema migration — touches the live `shakthi.db` and
should wait for the founder to have seen this document at least once.
