# DhanSetu + SHAKTHI_OS Error-Proofing & Confusion-Proofing Plan — v3.4

Date: 2026-09-13
Author: Claude Code (this session), evidence-based — grounded in a real
repository inventory (agent YAMLs, `db/schema.sql`, live dashboard pages)
plus real production checks performed the same session (Razorpay checkout
verified end-to-end on blackboxops.co.in, Google Search Console checked
live). Nothing below claims a system exists without a cited file, table,
or verified URL.

**Strict framing rule, honored throughout this doc and its three
companions:** nothing here is "100% error-proof." The goal is a
**failure-resistant system with approval gates and evidence tracking** —
failures still happen; the difference is they surface loudly, get a real
root cause, and don't repeat silently.

## 0. Headline finding

Most of what this mission asks for **already exists as real, working
infrastructure** — it was built across earlier SHAKTHI_OS work and never
consolidated into one plan. This document's job is mostly to **document,
formalize, and close real gaps** in that system, not invent a parallel one.
Specifically real and working today:

| Ask | Real backing |
|---|---|
| Failure memory (bug name, root cause, fix, prevention rule) | `bugs`, `bug_events`, `patches` tables + `dashboard/app/bugs/page.tsx` |
| 5-Whys / prevention record | `failure_analyses` table (`five_whys`, `root_cause`, `preventive_action`) |
| No-repeated-bugs detection | `bugs.occurrence_count` / `bugs.duplicate_of`, populated by real code in `bug_fixer`'s recurrence check |
| High-risk human approval gate | `decisions` table (`risk_score`, `business_impact_score`, `status: approved\|rejected\|revise`) + `ceo.yaml` agent contract; `bugs.status` has its own `ceo_approved`/`ceo_rejected` states |
| "No fake success" enforcement | `auditor.yaml` ("accept completion only when inspectable evidence exists") and `qa.yaml` (PASS/FAIL gate) — both real, existing agents |
| Staged, rollback-safe patches | `patches` table: a proposed fix is `full_file_path`/`diff_path` staged content, never written to the live file until `applied=true` |

Real gaps (confirmed absent, not just "unverified"):

| Ask | Real state |
|---|---|
| 7-state task lifecycle (IDEA→...→ARCHIVED) | `tasks.status` only has 3 values: `pending\|done\|failed`. No IDEA/ASSIGNED/BLOCKED states exist today. |
| LOW/MEDIUM/HIGH risk levels | `tasks.risk_level` only has 2 values: `normal\|critical`. |
| Competitor research agent | No existing agent does external competitor research. |
| Strategy/pricing/offer-stack agent | `business_analyst.yaml` is explicitly scoped to Stage-1 only ("do not recommend specific tools or automations yet"); no Stage-2 strategy agent exists. |
| On-site lead-capture bot | `buddy.yaml` is a family chat assistant, not a website visitor bot. No leads table confirmed. |
| Real 24/7 daemon (Watchdog) | `sentinel.py` exists (329 lines) but runs as an ad-hoc foreground process — **no systemd/launchd supervision**. Per the founder's own rule 5 in §7 below, this must be labeled "manual/check-based," not "24/7," until that changes. |
| `data/failure-memory.json` | Does not exist. See the companion doc for why this should be a generated export, not a hand-maintained parallel store. |

## 1. Error-proofing principles — real mechanism per principle

### 1. No silent failure
Real backing: `task_events` (`event_type: dispatch|validate_fail|escalate|result`) and `bug_events` (full lifecycle trail). Gap: `task_events` has no `severity` or `evidence_refs` column yet — a failed task's event row doesn't yet force "what/why/where/next action/owner" as structured fields, only a free-text `payload`. **Recommendation**: when a task fails, the `result` field must be a structured object with those 5 keys, enforced by convention in agent prompts (not a schema migration — lower risk, ships today).

### 2. No fake success
Real backing: `tasks.verification_status` (`unverified|verified|rejected`) + `verified_by`/`verified_at` already exist. `auditor.yaml` and `qa.yaml` already carry the "treat every result as a claim" doctrine. **This principle is already substantially enforced in the schema — the gap is that not every agent's prompt currently routes through `auditor.yaml`/`qa.yaml` before a task is marked done.** Recommendation: any agent producing a customer-facing or revenue-facing change routes through `qa.yaml` (PASS/FAIL) before `tasks.status` can become `done`.

### 3. No repeated bugs
Real backing: `bugs.occurrence_count`/`duplicate_of` already implements this for bugs. **Gap**: `failure_analyses` has no equivalent recurrence check — a second failure with the same root cause isn't automatically linked to the first. Recommendation (see companion doc): before creating a new `failure_analyses` row, search existing rows by `root_cause` substring match first.

### 4. No scan loop
Real, explicit policy (new, not previously codified): **dhansetuhub.in is BUILD, FIX, SELL, TRACK — never a repeat-scan target.** Audit/scanning agents (`security.yaml`, `website-health` checks) are scoped to *other/customer* websites by default. Any agent or session touching dhansetuhub.in should ask "am I building/fixing/selling/tracking, or am I re-scanning something already scanned?" before running another audit pass. This is a process rule for agents and for Claude Code sessions, not a code change.

### 5. No high-risk automation without a gate
Real backing: `decisions` table + `ceo.yaml`. Real gap: DNS changes, secret rotation, and production deploys performed by a Claude Code session (like this one, this session) currently go through **explicit chat confirmation with the founder**, not the `decisions` table — that's a real, working gate, just a different one than the bugfix pipeline uses. See `HIGH_RISK_APPROVAL_RULES.md` for the full mapping.

### 6. Safe automation continues
Real backing: the `blackboxops-os` worker already runs a real cron trigger (`*/5 * * * *`, confirmed in its `wrangler.toml`) for low-risk scheduled work. Drafting, docs, local builds/typechecks/tests (all used continuously this session) are already safe, unattended-capable work.

## 2. Agent roster — map to what's real, build only the genuine gaps

Building 9 brand-new agents would duplicate 6 that already exist. Real
mapping:

| Founder's role | Real agent(s) | Verdict |
|---|---|---|
| Master Shakthi Agent | `manager.yaml` (structures ambiguous requests) + `ceo.yaml` (approval scoring) + `pa_angella.yaml` (first-hop routing, per v3.3 audit only step 1 of a 12-step pipeline) | **Composite, not one agent.** Document this composite explicitly rather than building a redundant 4th "master" agent. |
| Researcher Competitor Market Agent | none | **Real gap — new agent needed.** |
| Strategy Maker Agent | none (`business_analyst.yaml` is Stage-1-only by its own prompt) | **Real gap — new agent needed.** |
| Website Implement Maker Agent | `website_builder.yaml` | Real, strong match. Already separates deterministic `generate_site()` pipeline from agent-authored copy — exactly the founder's "site exists is guaranteed, content is agent-authored" split. |
| 24x7 Watchdog Agent | `sentinel.py` (no supervision) + `website-health` dashboard (real data, no proactive alerts per prior verified memory) | Real code exists; **label as "manual/check-based" until a supervised daemon exists** — do not claim 24/7. |
| Site Security Protector Agent | `security.yaml` | Real, strong match. Prompt already says "do not invent findings." |
| On-Site Bot Agent | none (`buddy.yaml` is a family assistant) | **Real gap — new agent needed**, and needs a real lead-storage table (none confirmed today). |
| Money Calculator Agent | `finance.yaml` | Real, strong match. Already forbidden from inventing figures. |
| Bugfixer & Troubleshooting Agent | `bug_fixer.yaml` + `kaixen_bot.yaml` | Real, covered twice over. `kaixen_bot.yaml`'s own prompt already says "never invent a failure, root cause, successful repair, or production status" — verbatim the founder's own principle. |

Bonus real agents worth knowing about, not in the founder's original list:
`auditor.yaml` and `qa.yaml` — both already do exactly what "no fake
success" asks for.

**Action items**: write 2 new agent YAMLs (`competitor_researcher.yaml`,
`onsite_lead_bot.yaml`) plus a `strategy_maker.yaml` as Stage-2 successor
to `business_analyst.yaml`. Do not write new Master/Watchdog/Security/
Money/Bugfix agents — extend the real ones named above instead.

## 3. Task lifecycle — extend, don't replace

Target lifecycle:
`IDEA → STRUCTURED_TASK → ASSIGNED → IMPLEMENTING → VERIFYING → DONE → ARCHIVED`,
with `BLOCKED → ROOT_CAUSE → FIX_PLAN → RETRY → VERIFY` and
`FAILED → FAILURE_MEMORY → PREVENTION_RULE → NEW_TASK` branches.

Real state: `tasks.status` is `pending|done|failed` (3 values) —
`incidents.status` (a different, real, and more mature table) already has
an 8-state lifecycle: `NEW → ACKNOWLEDGED → INVESTIGATING → FIXING →
VERIFYING → READY_TO_DEPLOY → RESOLVED → CLOSED`. **This is the closest
real precedent** — the founder's target lifecycle is achievable by
extending `tasks.status` toward something shaped like `incidents.status`,
not inventing a new shape from nothing.

Recommended new `tasks.status` enum (additive migration, low risk):
`idea | structured | assigned | implementing | verifying | done | archived | blocked | failed`.
Existing rows keep working (`pending` maps to `structured`, `done`/`failed`
unchanged).

## 4. Risk levels — extend, don't replace

Real state: `tasks.risk_level` is `normal|critical` (2 values). Target is
LOW/MEDIUM/HIGH (3 values). Recommended migration: `normal → LOW` by
default, introduce `MEDIUM` explicitly, `critical → HIGH`. Every task
touching the categories in `HIGH_RISK_APPROVAL_RULES.md` gets `HIGH` and
must have a real `decisions` row (or, for Claude-Code-session actions,
real chat confirmation) before it can move past `assigned`.

## 5. Confusion-proofing rules (policy, not code)

1. **Operator Mode**: blackboxops.co.in — work on it directly, as this
   session already does (real deploys, real Razorpay verification, real
   Search Console checks this same session).
2. **Audit Mode**: any other/customer site — goes through Site Security
   Protector (`security.yaml`) / Website Health checks, not direct edits.
3. **Scan rule**: dhansetuhub.in gets manual before/after evidence scans
   only — never an auto-repeat scan loop. See principle 4 above.
4. **Revenue rule**: a revenue *target* (₹8,999 fast / ₹1cr long-term) is
   not revenue. `Money Calculator Agent` (`finance.yaml`) already only
   works from real ledger numbers — verified revenue stays ₹0 until a real
   `payments` row has `status = 'paid'` with a non-owner gateway (this
   session verified via direct D1 query that the one existing "paid" row
   is `gateway: owner_comp`, not a real sale).
5. **Agent truth rule**: an agent that is logical-only (a prompt, no
   runtime) must be labeled as such. `sentinel.py`/Watchdog is the clearest
   current example — real code, not yet a real always-on worker.
6. **Automation truth rule**: a task that only produced a prompt or a
   report is not "executed." This document itself follows that rule — it
   is a plan, not a deployed system, until the migrations and new agents
   in §2–4 are actually built and verified.

## 6. Backup and rollback

Already-real patterns this session used and that this plan formalizes:
- `git status` before any destructive operation (standing rule, already
  followed).
- The `patches` table's stage-then-apply model is a real, working rollback
  mechanism for code fixes — a patch is never live until `applied=true`.
- Before this session's own risky changes (pricing-tier restructure,
  PayU removal), real verification ran first: `npm run typecheck`,
  `npm test`, `npm run build`, then a local visual check, **then** deploy,
  **then** a real production curl/screenshot check — this is the concrete
  rollback-avoidance pattern to keep using for homepage/pricing/auth/
  payment/deploy changes going forward.

## 7. Cross-references

- `FAILURE_MEMORY_AND_BUGFIX_SYSTEM.md` — the real `bugs`/`failure_analyses`
  schema, and the `data/failure-memory.json` export design.
- `DHANSETU_REVENUE_READINESS_SCORECARD.md` — 12-category real scoring,
  evidence-cited, dated 2026-09-13.
- `HIGH_RISK_APPROVAL_RULES.md` — the real `decisions`/`bugs` gate mapped
  against the founder's required HIGH-risk categories.
