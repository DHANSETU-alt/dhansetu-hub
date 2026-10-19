# SHAKTHI_OS Phase 0 Audit — v3.2 → v3.3

Date: 2026-09-10 01:20 IST
Auditor: Claude Code (this session), evidence-based — every line below was
read from the real repository, a real running process list, or a real
schema file. Nothing here is inferred from naming alone.

## Current version

- `VERSION.txt`: `Shakthi_OS v3.2.0` — "Revenue Mission Engine", imported
  to Linux from a portable v3.1.1 snapshot taken 2026-09-03.
- Dashboard UI (fixed tonight): now displays `Shakthi_OS V6` per direct
  founder instruction. **This is a display-label change only — it has not
  touched a single line of orchestrator code.** The real, functional
  version of the system underneath remains v3.2.0-class. Treat "V6" as
  the founder's name for the *target* this audit is scoping, not as a
  completed version.

## Repository root / branch / commit

- Root: `/Users/apple/shakthi-os`
- Branch: `main`
- HEAD: `c788dbfce515760fbc33eb7faa0b87599ab75acc` —
  "Save checkpoint before PC restart: V6 mission work, CEO1/CEO2, Razorpay, Org Chart"
- Working tree: 9 modified files, all under `dashboard/` — tonight's real
  "Shakthi_OS V6" label + Zoeyos-style accent-bar/bracket-corner CSS work.
  Uncommitted, per this project's standing "never commit unless the
  founder asks" rule.
- Remote: `linux-3.2` → `blackboxops@100.86.74.97:ShakthiOS_v3.2` (the
  real Mac↔Linux Tailscale bridge referenced in prior session memory).

## Currently running services (real process list, not assumed)

| Process | PID | Since | Real? |
|---|---|---|---|
| `ollama serve` | 907 | 8:54 PM | Yes — real local model runtime, already running independent of this session |
| `python -m orchestrator.api` | 32811 | 12:15 AM | Yes — the real backend API (port 8787) this session started to unblock the dashboard |
| `next dev` (dashboard) | 32160 | 12:09 AM | Yes — this session's dashboard dev server |

No `systemd`/launchd-supervised long-running service exists for the core
scheduler, Guardian, or Sentinel — everything currently runs as an
ad-hoc foreground process started by hand or by a Claude Code session.
**Item 102 (Service Supervisor) target is not met: there is no supervised
service today.**

## Real database: `shakthi.db` (SQLite, 7.5MB, schema in `db/schema.sql`)

56 real tables exist. The ones most relevant to v3.3's core asks:

| v3.3 concept | Real table(s) | Actual shape |
|---|---|---|
| Task DAG | `tasks` | Flat list. Columns: `id, tenant_id, business_id, agent_id, goal, status(pending\|done\|failed), risk_level, result, created_at`. **No `parent_task_id`, no dependency edges, no DAG. This is a task list, not a graph.** |
| Task events | `task_events` | Real but minimal: `task_id, event_type(dispatch\|validate_fail\|escalate\|result), payload, created_at`. No `correlation_id`, no `worker`/`node`, no `severity`, no `evidence_refs` — the v3.3 Canonical Event (item 38) does not exist yet. |
| Durable workers | `workers` | Real but thin: `name, worker_type(rapid\|engineering\|infra), status(idle\|busy\|failed), concurrency_limit, tasks_completed, tasks_failed, last_active_at`. **No `lease`, no `heartbeat` freshness check, no `mailbox`, no `resource_budget`, no `permissions`/`toolset` per worker instance.** |
| Work queue | `work_queue` | Real: `kind, payload, priority, status(queued\|running\|done\|failed), assigned_worker_type, assigned_worker_id, result, error, timestamps`. This is a genuine priority queue — closest existing piece to item 10 (work-stealing scheduler), but there is no lease/steal logic confirmed yet (not read in this pass — flag for Phase 1 deep-read). |
| Agent identity | `agents` | Real, but static config, not a durable actor: `id, layer, name, default_model_tier(local\|cloud), local_model, allowed_scope(single_business\|cross_tenant), allowed_tools(JSON array), role_prompt, squad`. **This is the closest existing thing to a "Tool Capability System" (item 19) — allowed_tools already exists as a per-agent JSON allowlist — but it's authored config, not a runtime capability grant per task.** |
| Incident pipeline | `incidents`, `incident_events` | **Genuinely mature.** Real status lifecycle: `NEW → ACKNOWLEDGED → INVESTIGATING → FIXING → VERIFYING → READY_TO_DEPLOY → RESOLVED → CLOSED`, severity `P0-P3`, `root_cause`, `fix_applied`, `detected_by(manual\|incident_scheduler)`, `recovery_action`/`recovery_result`. This already substantially satisfies v3.3 item 39's DETECT→CLASSIFY→ROOT CAUSE→VERIFY shape — closer to target than almost anything else audited. |
| Cost tracking | `cost_ledger` | Table exists (not read in depth this pass — Phase 1 follow-up). |
| Memory | `memory_entries` | Table exists, single flat table — no evidence yet of the v3.3 working/episodic/semantic/procedural/failure-memory separation (item 50). Needs a Phase 1 read of `orchestrator/knowledge.py` (only 27 lines — likely thin) to confirm. |
| Skills | `skill_reviews` | Table exists but named for *human* skill reviews (a PeopleDesk/HR-adjacent table per surrounding schema), not agent-skill lifecycle (item 52's OBSERVE→EXTRACT→GENERALIZE→TEST→PUBLISH). **No agent skill metabolism engine exists.** |
| Policy engine | `orchestrator/access.py` (36 lines) | Real but minimal: `identify(passphrase)` and `allowed(identity, action_category) -> bool`. A single binary allow/deny check, not the ALLOW/DENY/REQUIRE_APPROVAL/SANDBOX_ONLY/ALLOW_WITH_LIMIT decision engine item 20 wants. |
| Model gateway | `orchestrator/model_gateway.py` (89 lines) | Real and working — genuinely calls Ollama (`call_local`) and Anthropic Claude (`call_cloud`), with a real cost estimator. **Only two providers, no Codex, no OpenAI as a distinct provider, no `capabilities()/availability()/latency()/health()/stream()/cancel()` — a real but early-stage version of item 13's AgentGateway, not the full abstraction.** |
| Guardian | — | **Does not exist as a named subsystem.** One incidental match (a comment in `backup_manager.py`). Item 61 (Guardian v3) has no v1 or v2 to build from — this is a from-scratch subsystem. |
| Sentinel | `orchestrator/sentinel.py` (329 lines) | Real, substantial file — the most mature monitoring piece that exists. Not read in depth this pass; Phase 1 should confirm exactly what it watches today vs. item 62's target list (agents, daemons, automations, databases, queues, models, storage, nodes, backups). |
| Angella | `orchestrator/pa_angella.py` (132 lines) | **Real, but scoped narrowly.** Confirmed by reading the actual code: Angella's job today is "take the founder's raw/informal message, refine it into a clear prompt, hand it to `ceo.decide()`." That's prompt refinement + one hop of routing — not a Mission Compiler, not DAG planning, not resource/agent assignment, not verification, not lesson extraction. **Every stage of the v3.3 item 5 pipeline past "CONTEXT ASSEMBLY" does not exist yet.** |
| Multi-model routing | `orchestrator/routing.py` (234 lines) | Real dispatch exists (`routing.run_task` is called by Angella and presumably other agents) — not read in depth this pass. Needs Phase 1 read to confirm whether routing decisions use any of item 14's signals (complexity, cost, latency, historical success) or are static per-agent (`default_model_tier` on the `agents` table suggests the latter — static, not adaptive). |

## Backup system

- `orchestrator/backup_manager.py` — 326 lines, real code (not a stub).
- `BACKUP_CHECKLIST.md` exists at repo root — a real, human-authored
  checklist, not a script.
- The 3×3 resilience fabric (item 63: LOCAL / EXTERNAL SSD / REMOTE ×
  3 generations) does **not** exist as an implemented system. Tonight's
  session confirms real, current state: **no external drive is plugged
  into this Mac**, so the SSD leg of even a simple 2-copy backup is
  pending on the founder physically connecting one — this was already
  in progress as a separate task this same session, still blocked on
  that.
- A real portable snapshot precedent exists: `VERSION.txt` documents a
  full working copy (code + `shakthi.db`) taken 2026-09-03 for the Linux
  migration, with a `PLUG_AND_PLAY.py` bootstrapper. That snapshot
  mechanism is real prior art for the "generation" concept in item 63,
  just not automated or verified via restore drills (item 65).

## Browser/computer automation

- `orchestrator/chrome_developer.py` exists (real file, not sized/read
  this pass). Confirmed elsewhere in this same session: browser
  automation (`mcp__claude-in-chrome__*`) was used extensively and for
  real, verified outcomes tonight (Cloudflare DNS, Razorpay dashboard,
  Google Search Console) — but that was this Claude Code session's own
  tool use, not `chrome_developer.py`'s own code path. Whether
  `chrome_developer.py` implements item 72's "prefer API → CLI →
  structured GUI automation → visual computer use" ordering is
  unconfirmed — Phase 1 follow-up.

## Model integrations — real vs. claimed

- **Ollama**: real, confirmed running (PID 907) and reachable via
  `model_gateway.call_local`.
- **Claude/Anthropic**: real code path in `model_gateway.call_cloud`,
  gated on `ANTHROPIC_API_KEY` being set — not confirmed set or unset
  this pass (do not assume either way without checking `config.py`/env
  in Phase 1).
- **Codex / OpenAI as a distinct provider**: no evidence found in
  `model_gateway.py`. If Codex integration exists, it lives outside this
  file — Phase 1 must locate it before item 13's AgentGateway can honestly
  claim multi-provider support.

## Test status

- 43 real test files under `tests/`. Not executed this pass (time
  budget) — Phase 1's first action should be `pytest` end-to-end to get a
  real pass/fail count before touching any code, per the founder's own
  "MIGRATION SAFETY" instruction (item 129).

## Known, already-documented failures (from this repo's own files, not invented)

- `CEO_FAILURE_REPORT.md`, `CEO_HARDENING_PLAN.md` — the CEO agent has a
  documented history of real failures already analyzed by a prior
  session.
- `SYSTEM_HARDENING_REPORT.md`, `ZERO_SINGLE_POINT_FAILURE_PLAN.md` —
  prior real resilience work exists; Phase 1 should read these before
  re-deriving the same analysis from scratch.

## Phase 1, day 1 — completed tonight (real, verified)

- **Full test suite run**: `476 passed, 0 failed` (32 deprecation
  warnings, all `datetime.utcnow()` — real but minor, not urgent).
  This is the honest baseline the founder's spec asked for before any
  Phase 1 code changes.
- **Secret-handling check, `orchestrator/config.py`**: `ANTHROPIC_API_KEY`
  is read once via `os.environ.get(...)` into a module-level constant,
  used only inside `model_gateway.call_cloud()` to construct the
  `anthropic.Anthropic(api_key=...)` client. **No evidence of the key
  reaching a prompt, a log line, or the dashboard in the code read this
  pass.** The Secret Broker (item 22) is still a real architectural gap —
  there's no formal brokering layer, so a future careless addition could
  still leak a key — but there is no active leak today. Downgrade this
  from "verify before building anything else" to "real gap, not an
  active incident."
- **Bonus real finding, same file**: `CLOUD_DAILY_BUDGET_USD`,
  `ALLOW_EXEC`, and `TOOLS_DRY_RUN` env-gated config already exist —
  real, if partial, prior art for item 42 (Autonomy Budget) and item 23
  (Sandbox First / dry-run). Phase 1's architecture proposal should
  extend these rather than invent parallel new ones.

## Headline conclusion

SHAKTHI_OS today is a **real, working, single-machine agent-dispatch
system with a genuinely mature incident pipeline and a thin-but-real
two-provider model gateway** — not a mock, not prompt-only theater. But
it is a **flat task list with a static agent-config table**, not the
durable-actor / DAG / policy-engine / multi-node platform v3.3 describes.
The gap is real and large, concentrated in exactly the areas the founder's
spec calls out: Task DAG (item 8), durable workers with leases/heartbeats
(item 3), a real policy engine (item 20), Guardian as an independent
subsystem (item 61), and Angella evolving past prompt-refinement into an
actual Mission Compiler (items 5-6). The incident pipeline, work queue,
and model gateway are the strongest existing foundations to build the
first vertical slice on top of, precisely because they're already real.
