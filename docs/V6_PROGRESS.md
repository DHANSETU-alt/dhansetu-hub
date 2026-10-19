# SHAKTHI_OS v6 — Progress Log

Format per day: OBJECTIVE, STATUS, FILES CHANGED, TESTS RUN, RESULT, EVIDENCE, KNOWN ISSUES, NEXT ACTION.
Never fabricated — every line below is something actually executed and observed, not assumed.

---

## DAY 1 — 2026-09-08

**OBJECTIVE:** Freeze current baseline. Create git tag/backup. Record current build/test/runtime status.

**STATUS:** DONE

**FILES CHANGED:**
- Created `backups/shakthi_before_v6_baseline_2026-09-08.db` (DB snapshot, 5.1MB)
- Created `/Users/apple/shakthi_os_backup_20260908_185944_v6_baseline.tar.gz` (full repo tarball, 16MB, excludes node_modules/.next/__pycache__)
- Created annotated git tag `v6-baseline-2026-09-08` at commit `33236ad`
- Created this file (`docs/V6_PROGRESS.md`)

**TESTS RUN:**
```
cd /Users/apple/shakthi-os && python3 -m pytest -q
```

**RESULT:** 449 passed, 0 failed, 31 warnings (all `datetime.utcnow()` deprecation notices — non-blocking) in 93s.

**EVIDENCE:**
- `git rev-parse v6-baseline-2026-09-08` → `5d16b6d` (tag object) pointing at `33236ade5c3788b6467dbcba193dd4e2908ecf6e`
- `git log --oneline -5` → last real commit was the Mac/Linux tailnet CORS allowlist change (2026-09-06); before that, the sync_bridge.py Mac↔Linux bridge (now retired, see below)
- Dashboard confirmed live and rendering correctly at http://localhost:3000 (verified in-browser this session)
- API confirmed live at http://127.0.0.1:8787/api/health
- `npm run build` in `dashboard/` completed successfully — all ~60 routes compiled clean, no type/build errors

**KNOWN ISSUES:**
1. **Working tree is not clean at tag time.** Two unrelated sets of uncommitted changes exist on top of the tagged commit:
   - This session's Mac-only separation work (8 files modified, `orchestrator/sync_bridge.py` deleted) — tested, dashboard verified working live in Chrome.
   - Pre-existing uncommitted edits to `agents/pa_angella.yaml`, `orchestrator/pa_angella.py`, `orchestrator/founder_review.py` from an earlier session (per memory: Angella hourly pending-task-push wiring; an E2E test was recorded as failing, exit 1, and never confirmed fixed). Current pytest suite passes, but that may not cover the specific E2E path that failed — **do not assume it's fixed without re-running that specific check.**
   - Neither set has been committed. Recommend committing them as two separate commits (they're unrelated) before Day 2 starts, once the Angella E2E concern above is re-verified.
2. **`shakthi/angela.py` is a second, disconnected "Angella" concept** (mission drafting with fictional `Thinker/Planner/Critic/Judge` sub-agents, `AutonomyLevel` enum) that appears unused by the live pipeline. The real, live Angella is `orchestrator/pa_angella.py` + `agents/pa_angella.yaml`. This divergence needs a decision in the v6 architecture pass (Day 7): merge, repurpose, or delete.
3. No prior git tags existed in this repo before today — this is the first frozen baseline.

**NEXT ACTION:** Day 2 — map repository structure (frontend/backend/database/agent systems) into the V6 architecture decision record.

---

## DAY 2 — 2026-09-08

**OBJECTIVE:** Map repository structure. Identify frontend/backend/database/agent systems.

**STATUS:** DONE

**FILES CHANGED:** None — documentation-only day, findings recorded here.

**TESTS RUN:** N/A (no code touched).

**RESULT / REAL MAP:**

- **Frontend** — `dashboard/`: Next.js app, ~60 routes under `app/`, 17 shared components under `components/`. Real deps: `@xyflow/react` (the agent graph), `framer-motion` (all the orb/ring/glow animation), `recharts`, Tailwind. `npm run build` verified clean (Day 1). Talks to the backend only via `lib/api.ts` → `http://127.0.0.1:8787` (or `API_BASE`/`NEXT_PUBLIC_API_BASE` env override).
- **Backend** — `orchestrator/`: 78 Python modules (~15,300 LOC), stdlib `http.server`-based API (`api.py`, no framework), CLI (`cli.py`), and one module per business/governance domain (finance, sales, marketing, security, sentinel, incident_manager, etc.). A second, smaller subsystem lives in `shakthi/` (17 modules, ~1,400 LOC): telemetry, world model, governance, missions, event bus — real but thinner, and where the divergent second "Angella" concept lives (see Day 1 risk #2, and Day 3 below).
- **Database** — SQLite at `shakthi.db`, schema in `db/schema.sql`, **63 tables**. Explicitly documented in the schema's own header as a *dev-mode stand-in* for a future Postgres + pgvector schema — `tenant_id` is already on every row specifically so that migration is "a data migration, not a redesign" when it happens. This is real, acknowledged tech debt, not an oversight (carried into Day 5's audit).
- **Agent systems** — YAML-driven registry (`agents/*.yaml` → `registry.sync_registry()` → `agents` table), 27 agents (Day 1), organized into 6 founder-named squads: **Get Shit Done** (8), **GStack** (7), **Front End Design** (6), **Superpower** (4 — includes `ceo`, `pa_angella`, `manager`, `dhansetu_manager`), **Emergency Response** (1 — `kaixen_bot`), **Revenue Mission Engine** (1). Routing/model-selection/cost-tracking is centralized in `routing.py` + `model_gateway.py`, not scattered per-agent.

**EVIDENCE:** `ls dashboard/app` (60 route dirs), `ls dashboard/components | wc -l` → 17, `grep -h squad: agents/*.yaml | sort | uniq -c` → the 6-squad breakdown above, `grep CREATE TABLE db/schema.sql | wc -l` → 63 (Day 1 listing).

**KNOWN ISSUES:** None new — the `shakthi/angela.py` divergence (Day 1) is the one structural risk this map reinforces: two real subsystems (`orchestrator/` and `shakthi/`) exist side by side with a live/dead-code split, not a clean layered architecture.

**NEXT ACTION:** Day 3 — document current Angella implementation.

---

## DAY 3 — 2026-09-08

**OBJECTIVE:** Document current Angella implementation.

**STATUS:** DONE

**FILES CHANGED:** None — documentation-only day.

**TESTS RUN:** N/A.

**RESULT:**

Live Angella = `agents/pa_angella.yaml` (registry entry: squad Superpower, layer coordination, local model `llama3.2`, cross-tenant scope, no tool access) + `orchestrator/pa_angella.py` (120 lines, 4 functions):

- `refine_prompt(raw_message)` — the core of what Angella does today: takes the founder's raw/informal message, runs it through `routing.run_task("pa_angella", ...)`, returns a cleaned, professional restatement. Explicitly instructed (role_prompt) to never add unstated requirements and to flag ambiguity as an open question rather than guess.
- `refine_and_speak(...)` — same, then speaks the result back via `voice.py`'s TTS (macOS `say`, female voice by default).
- `refine_and_send_to_ceo(...)` — chains refinement straight into `ceo.decide()`, the founder→Angella→CEO direction.
- `push_pending_work(snapshot)` — the other direction: CEO/system state → Angella → founder. Wired to real hourly cron (`--founder-review` in crontab, confirmed Day 1 despite no literal "angella" string in crontab). Real two-call design (English reasoning on `llama3.2`, then a separate translation call) — found necessary live because asking one call to reason over 20+ initiatives AND translate AND hold format broke down (24+ min hang, confirmed and killed).

**What Angella is NOT yet, per the v6 brief's own definition of "orchestrator":** no planner, no task router beyond the fixed founder→CEO chain, no delegation to arbitrary specialist agents, no supervision/follow-up loop, no personality-mode switching, no live continuous mic session (voice.py's `listen_loop` exists as real infrastructure but nothing currently calls it from Angella), no L0-L9 memory layering.

**Real risk restated with more detail (Day 1 risk #2):** `shakthi/angela.py` (40 lines) is a disconnected prototype — `draft_mission()` builds a `Mission` dataclass with a fictional `["Thinker", "Planner", "Critic", "Judge"]` sub-agent list and an `AutonomyLevel` enum, keyword-classifies goals into `PaymentOps`/`Software Factory`/`Mission Control` departments. Nothing in `orchestrator/` imports or calls it — confirmed via `grep -rn "from shakthi.angela\|shakthi import angela" orchestrator/` returning nothing. It's real code, real design thinking, but dead relative to the live pipeline.

**EVIDENCE:** Direct read of `orchestrator/pa_angella.py`, `shakthi/angela.py`, `agents/pa_angella.yaml`; crontab confirmed hourly `--founder-review` entry (Day 1); grep confirming zero live callers of `shakthi/angela.py`.

**KNOWN ISSUES:** Same E2E-test concern as Day 1 (pre-existing uncommitted `pa_angella.py` changes, last recorded E2E failure unresolved) — still not re-verified, still blocking before any orchestrator work builds on this file.

**NEXT ACTION:** Day 4 — document current agent roster and orchestration.

---

## DAY 4 — 2026-09-08

**OBJECTIVE:** Document current agent roster and orchestration.

**STATUS:** DONE

**FILES CHANGED:** None — documentation-only day.

**TESTS RUN:** N/A.

**RESULT — real roster (27 agents, id / squad / layer / model):**

```
buddy                         Get Shit Done          business      llama3.2   family assistant
bug_fixer                     Get Shit Done          governance    gemma4     staff-level bug triage/fix
business_analyst              Get Shit Done          business      llama3.2   AI Employee Stage 1 intake analysis
ceo                           Superpower              executive     gemma4     approve/reject/revise scoring
chrome_developer               Front End Design       engineering   llama3.2   browser-driven dev work
content_scheduler              Front End Design       business      llama3.2   Dhansetu content scheduling
correction_bot                 Get Shit Done          governance    llama3.2   final QA reviewer
course_writer                  Front End Design       business      llama3.2   Dhansetu course authoring
customer_success               Get Shit Done          business      llama3.2   onboarding/support drafting
data_intelligence               GStack                 intelligence  gemma4     cross-business metrics
dhansetu_manager                Superpower              coordination llama3.2   Dhansetu coordinator
email_handler                   GStack                 operations    llama3.2   inbound email handling
engineer                        GStack                 engineering   gemma4     general code writing
finance                         Get Shit Done          business      llama3.2   real-numbers finance summaries
kaixen_bot                      Emergency Response     governance    qwen3:4b   continuous troubleshooting
knowledge                       GStack                 operations    llama3.2   stored-doc Q&A
manager                         Superpower              operations    llama3.2   founder request → scoped task
marketing                       Get Shit Done          business      llama3.2   top-of-funnel content
memory                          GStack                 operations    llama3.2   task → memory_entries writer
pa_angella                      Superpower              coordination llama3.2   founder-facing refiner (Day 3)
prompt_writer                   Front End Design       business      llama3.2   Dhansetu AI-prompt writing
qa                              GStack                 engineering   llama3.2   validates another agent's output
reel_scripter                   Front End Design       business      llama3.2   Dhansetu shot-by-shot scripts
revenue_mission_project_head    Revenue Mission Engine  executive    llama3.2   Revenue Mission Engine lead
sales                           Get Shit Done          business      llama3.2   outreach/proposal drafting
security                        GStack                 governance    llama3.2   security posture reporting
website_builder                 Front End Design       engineering   llama3.2   site generation
```

**Orchestration mechanics (real, in `routing.py` + `model_gateway.py`):**
1. `run_task(agent_id, goal, business_id)` classifies risk via keyword match: `CRITICAL_KEYWORDS` (refund, cancel subscription, contract, legal, production database, delete all, credentials...) → critical; `HIGH_KEYWORDS` (deploy to production, go live, launch campaign, security incident...) → high; `LOW_KEYWORDS` → low; else normal.
2. Normal/high risk → local model only (`call_local`, Ollama). Critical risk → tries cloud first (`call_cloud`, Anthropic), with a **lazy local fallback** if cloud fails (no key, or the `anthropic` package isn't installed — it's commented out in `requirements.txt` by default, Day 5) — this was itself a deliberate fix (comment: an earlier version returned zero judgment at all on the highest-stakes goals when cloud was unavailable).
3. Every call logs to `cost_ledger` (provider, tokens, `$` estimate) and `task_events` (dispatch/validate_fail/escalate/result) — this is the real audit trail the v6 brief asks for, already half-built.
4. `NO_MEMORY_CONTEXT` — 9 agents (`pa_angella`, `business_analyst`, `marketing`, `sales`, `customer_success`, `knowledge`, `course_writer`, `prompt_writer`, `reel_scripter`, `content_scheduler`) are deliberately excluded from automatic memory-context injection, after 3 separate confirmed-live incidents of stale/unrelated memory leaking into their output as if it were the current brief.

**EVIDENCE:** `sqlite3 shakthi.db "SELECT ... FROM agents"` (Day 1), direct read of every `agents/*.yaml` role_prompt first line, direct read of `routing.py` (`classify_risk`, `run_task`, `NO_MEMORY_CONTEXT`) and `model_gateway.py` (`call_local`, `call_cloud`).

**KNOWN ISSUES:** No agent-level `risk_level`, `max_runtime`, `health_score`, `success_rate`, or `memory_scope` fields exist on the `agents` table itself (Day 1 gap analysis) — the dashboard's "Agent Health Monitor" computes health from the `tasks` table at query time rather than storing it, which is actually a defensible real-data-over-cached-field choice, not automatically a gap to fix.

**NEXT ACTION:** Day 5 — audit dependencies and technical debt.

---

## DAY 5 — 2026-09-08

**OBJECTIVE:** Audit dependencies and technical debt.

**STATUS:** DONE

**FILES CHANGED:** None — documentation-only day.

**TESTS RUN:** `python3 -m pytest -q` re-run to confirm Day 1's 449/449 still holds after Days 2-4's (docs-only) changes.

**RESULT:** 449 passed, 0 failed (unchanged from Day 1 — expected, since no code changed).

**Dependency audit (real, from `requirements.txt` and `dashboard/package.json`):**

- Backend deps are minimal and deliberate: `pyyaml`, `google-api-*`, `psutil`, `pypdf`+`Pillow` (PDF Studio), `faster-whisper`+`sounddevice`+`numpy` (voice). No heavyweight ML/web framework — the API layer is stdlib `http.server` by design.
- **`anthropic` is commented out** in `requirements.txt` — "Optional — only needed to enable Claude escalation." This reframes Day 1/3's "cloud escalation unavailable" finding: it's not a broken feature, it's an *undeployed optional dependency* the founder never opted into on this machine. Fixing it is a `pip install anthropic` + set `ANTHROPIC_API_KEY`, not an engineering task.
- Frontend deps are current and reasonable: Next.js, `@xyflow/react` (agent graph), `framer-motion` (all animation work incl. today's core rework), `recharts`, Tailwind, TypeScript, Playwright (present as a devDependency — worth checking Day 88's "regression testing" whether it's actually wired to any test files yet, or just installed).

**Known, self-documented technical debt (found in the code's own comments, not inferred):**
1. **SQLite, not Postgres** — `db/schema.sql`'s own header calls this a "dev-mode stand-in," with `tenant_id` on every row specifically to make the eventual migration additive. Real, acknowledged, not yet urgent at current single-tenant/single-machine scale.
2. **31 `datetime.utcnow()` deprecation warnings** across the test suite (customer_success.py, governor.py, incident_manager.py, pricing.py, sales.py) — Python's stdlib deprecation, not yet breaking, but will need a mechanical `datetime.now(UTC)` sweep before whatever Python version actually removes it.
3. **`shakthi/angela.py`** — dead code relative to the live pipeline (Day 3). Needs an explicit decision (delete / merge / repurpose), not indefinite coexistence.
4. **Ollama timeout tuned for short prompts** — `OLLAMA_TIMEOUT_SECONDS=420` was itself raised once already (180s → 420s) after real observed 2:24-3:26 gemma4 calls; today's CEO-decision attempt still exceeded it on a long/complex goal (Day 1). The fix path is already implied by `pa_angella.py`'s own precedent (split into a smaller multi-call chain for long inputs), not a bigger timeout.
5. **No agent-level operational metadata** (Day 4) — `max_runtime`/`health_score`/`success_rate`/`memory_scope` per agent, called for by the v6 brief, don't exist as stored fields yet.

**EVIDENCE:** Direct read of `requirements.txt` (the commented-out `anthropic` line) and `dashboard/package.json`; pytest warning output (Day 1's own captured run); direct grep/read of the five items above in their source files.

**KNOWN ISSUES:** None new beyond the five items above, all now tracked in one place instead of scattered across Day 1/3/4 findings.

**NEXT ACTION:** Day 6 — audit security/secrets/configuration (not yet started).

---

## DAY 6 — 2026-09-11

**OBJECTIVE:** Resume after restart; re-verify the Angella handoff path and harden offline/degraded runtime boundaries discovered during validation.

**STATUS:** DONE (runtime resilience) / SECURITY SCAN IN PROGRESS

**FILES CHANGED:**
- `orchestrator/routing.py` — memory enrichment is now best-effort; an Ollama outage records a `memory_unavailable` event without failing the parent business task.
- `orchestrator/sentinel.py` — unavailable macOS `cpu_freq` and `swap_memory` readings degrade to honest `None` values instead of crashing health collection.
- `shakthi/telemetry.py` — unavailable swap and boot-time readings are reported as `UNAVAILABLE` while the remaining telemetry remains live.

**TESTS RUN:**
- `python3 -m pytest -q tests/test_pa_angella.py tests/test_v31_control_plane.py` → 10 passed.
- `python3 -m pytest -q` → **478 passed, 0 failed, 33 warnings**.
- `npm run build` → blocked by offline Google Fonts fetch in `next/font` (`fonts.googleapis.com`); no source/type error was reported.

**RESULT / EVIDENCE:** The previously unresolved Angella-focused path passes. The full suite also passes when Ollama is unavailable and macOS telemetry permissions are restricted, matching the project's local-first/degraded-mode contract.

**KNOWN ISSUES:** 33 existing `datetime.utcnow()` deprecation warnings remain. The standard Codex Security scan is registered for this repository and remains resumable; its canonical report is not yet complete.

**NEXT ACTION:** Day 7 — decide the fate of the disconnected `shakthi/angela.py` prototype, then continue the V6 architecture pass.

---

## PARALLEL TRACK — Upkeeper for Mac (Project 2), finished to real v1.0.0 — 2026-09-08

Not part of the numbered Angella/v6 day sequence — a real, separate product (`blackboxops-cleaner` / Upkeeper.app) that was already at 100% of its recorded milestones (Shakthi_OS Project 2) but stuck at placeholder build metadata. Folded in here per founder request to track it alongside v6 rather than in a separate thread.

**OBJECTIVE:** Take Upkeeper from "all milestones done, still 0.0.0/ad-hoc/no installer" to a real distributable v1.0.0.

**STATUS:** DONE (packaging) / BLOCKED (real code signing — see below)

**FILES CHANGED:**
- `Upkeeper.spec` — bundle_identifier `com.blackboxops.upkeeper` (was `None`), version `1.0.0` (was `0.0.0`), added `NSHumanReadableCopyright`/`LSMinimumSystemVersion`/`NSHighResolutionCapable` to Info.plist.
- Rebuilt `dist/Upkeeper.app` via PyInstaller (pyinstaller 6.22.2, installed fresh — wasn't present in this Python env).
- Built `dist/Upkeeper-1.0.0.dmg` (22.7MB) via `hdiutil create -format UDZO`.
- `orchestrator/cli.py` — fixed a real, unrelated bug found while updating this initiative: `_cmd_milestone_add`/`_cmd_initiative_status` always printed "Task N" regardless of actual track, mislabeling Project/OS-track items. Now uses the same track→label logic `_cmd_initiative_add` already had.

**TESTS RUN:** `python3 -m pytest -q` in `blackboxops-cleaner/` (28 tests) and in `shakthi-os/` (449 tests, `-k "initiative or cli"` subset for the cli.py fix).

**RESULT:**
- 28/28 Upkeeper tests pass, 449/449 Shakthi_OS tests pass (cli.py fix included).
- Live smoke test: launched the rebuilt `.app`, confirmed `http://127.0.0.1:8420/` returns real 200, quit cleanly.
- `hdiutil verify` on the DMG: checksum VALID.
- Shakthi_OS Project 2 initiative marked `done` (was stuck at `running` despite 5/5 milestones); new milestone #186 records the real packaging work.

**KNOWN ISSUES — FOUNDER ACTION REQUIRED:**
Code signing is still **ad-hoc only** (`security find-identity -v -p codesigning` → 0 valid identities on this Mac). This is not fixable by more engineering work — it needs the founder to enroll in the Apple Developer Program ($99/yr) and install a real Developer ID certificate. Until then: Gatekeeper will warn/block on any other Mac, and Mac App Store submission isn't possible at all.

**NEXT ACTION:** Once a real Developer ID exists, re-sign (`codesign --deep --force --sign "<Developer ID>"`) and notarize before distributing outside this machine.

---

## PARALLEL TRACK — Upkeeper real pricing + licensing — 2026-09-08

**OBJECTIVE:** Ship real pricing (founder decision: ₹499 one-time/1yr, ₹3000 one-time lifetime+updates) with a working purchase→activation flow, for a product that ships as a distributed binary (not a page on a server the founder controls).

**STATUS:** DONE (code) / BLOCKED (real Razorpay keys, same gap as blackboxOps_OS pricing)

**KEY DECISION:** Did NOT reuse the embedded Checkout.js pattern built earlier tonight for the web pricing page. That pattern requires the Razorpay Key Secret to reach the browser's request; fine for a page the founder's own server renders, but Upkeeper is a PyInstaller `.app` distributed to buyers' machines — embedding the secret there would let anyone decompile it out. Used real Razorpay **Payment Links** instead (founder-generated, safe to embed as a plain URL) plus an offline HMAC-signed license-key scheme so the app can verify a purchase without ever holding the merchant secret.

**FILES CHANGED:** `cleaner/license.py` (tiers, expiry, key generation/verification), `cleaner/payments.py` (new, Payment Link creation), `app.py` (activate route + pricing in `/api/report`), `templates/index.html` (Buy/Activate UI), rebuilt `dist/Upkeeper.app` + `dist/Upkeeper-1.0.0.dmg`.

**TESTS RUN:** `python3 -m pytest -q` in `blackboxops-cleaner/` → 43/43 pass (15 new, including forged-signature/tampered-key attack tests).

**RESULT:** Full purchase→activate loop verified live end-to-end against the rebuilt packaged `.app` (not just the dev server): generated a real key, activated it via the live UI, confirmed `Status: Licensed · 1 year · valid until 2027-09-08`, reverted the test license afterward so the real machine shows its true unlicensed state.

**KNOWN ISSUES — FOUNDER ACTION REQUIRED:** Buy buttons show "Not available yet" until real Razorpay keys exist. Once they do: `python3 -m cleaner.payments <key-id> <key-secret>` generates the two real links; paste them into `app.py`'s `BUY_LINK_ANNUAL`/`BUY_LINK_LIFETIME` and rebuild.
