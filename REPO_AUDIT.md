# REPO_AUDIT.md — Shakthi_OS baseline (2026-09-16)

Section 1 of the V5.5 Founder Engineering Execution Contract. Evidence-based; everything below was directly observed this session, not inferred.

## Repository truth

- Path: `/Users/apple/shakthi-os`. Branch `main` @ `c788dbf` ("Save checkpoint before PC restart: V6 mission work, CEO1/CEO2, Razorpay, Org Chart").
- Remote: `linux-3.2 -> blackboxops@100.86.74.97:ShakthiOS_v3.2` (SSH to the Linux box's Tailscale IP, bare-repo style). **No GitHub remote.**
- Working tree is dirty: 39 modified/deleted tracked files, 38 untracked paths (77 total). Not touched or discarded — left exactly as found. Notable untracked items: `AGENTS.md`, `.claude/`, `.mcp.json`, `agents/*.yaml` (4 new agent defs), `orchestrator/security_policy.py` + its test, `orchestrator/skills_library.py` + its test, `scripts/`, `data/`, `dhansetu-web/`, a whole `linux_backup_before_wipe_20260913/` tree. This is real in-progress work from a prior session — protect it before any branch/worktree operations.
- Test baseline: `python3 -m pytest tests/ -q` → **488 passed, 0 failed, 33 warnings** (132s). All warnings are the same class: `datetime.datetime.utcnow()` deprecated, across `chrome_developer.py`, `correction_bot.py`, `customer_success.py`, `governor.py`, `incident_manager.py`, `pricing.py`, `sales.py`. Minor, non-blocking, real.

## Critical finding: "Shakthi_AI" does not exist in code

The founder correction states Shakthi_AI is "the existing Shakthi_AI implementation" that Jarvis/Angella were deleted and replaced by. Directly checked:

- `git grep -i "shakthi_ai\|shakthi-ai"` across tracked `.py`/`.ts`/`.tsx` → **0 matches.**
- Same search including untracked files and `.md` → **0 matches** anywhere in the repo.
- `git grep -i "jarvis\|angella"` across tracked `.py`/`.ts`/`.tsx` → **31 files**, actively modified in the current dirty tree (not stale/dead code): `orchestrator/jarvis_mediator.py` (+ `tests/test_jarvis_mediator.py`), `dashboard/app/jarvis/`, `dashboard/app/api/jarvis/`, `dashboard/components/JarvisVoiceControl.tsx`, `dashboard/components/JarvisMissionGraph.tsx` (untracked, i.e. brand new), `dashboard/components/AngellaPresence.tsx`, and more.

**Nuance that matters for scoping:** `orchestrator/jarvis_mediator.py` is only 65 lines. Its own docstring: *"This module does not execute tools... the existing Voice Commander retains identity, risk, approval, execution and audit responsibility."* It's a voice-transcript language-detection/normalization helper, not a coordinator. The actual task-dispatch entrypoint is `orchestrator/routing.py::run_task()` (274 lines: `classify_risk` → dispatch → `_validate` → `_try_cloud` escalation → `_maybe_execute_tool` → `_write_memory`) — unbranded, no Jarvis/Angella naming in it.

**What this means:** there is no pre-existing "Shakthi_AI" system to migrate integrations *into* — it doesn't exist under that name or an equivalent architecture. The mission-kernel described in Section 3 of the contract (MissionSpec, DAG compilation, leases/fencing tokens, QUEUED/RUNNING/VERIFYING/... state machine) also does not exist yet; `run_task()` is a single synchronous dispatch function, not a scheduler. Both are real gaps to build, not rename targets.

**Open question this blocks** (flagged to founder rather than guessed): is "Shakthi_AI" (a) the *new name* for what gets built in Section 3 (mission kernel), with Jarvis-branded UI/voice components renamed as a cleanup pass once it lands, or (b) something the founder believes already exists elsewhere (different branch, the Linux-side `ShakthiOS_v3.2` remote, or a different machine) that I haven't located? Answer changes whether the Jarvis rename is this session's next task or premature.

## Live defect found and fixed this session

`dashboard/app/page.tsx` (Executive Dashboard) set `<AutoRefresh intervalSeconds={1} />`, but each server render does a live SSH round-trip to the Linux node (`getLinuxRuntime()`) plus a Mac runtime check, taking 1.2–3.2s per request (confirmed in `logs/dashboard.log`). The 1s timer fired a new fetch before the prior one resolved, producing repeated `Error: The destination stream closed early` and `Failed to fetch RSC payload` — this was the "Executive Dashboard error" reported live. Fixed by raising the interval to 5s; verified clean 200s with no stream errors afterward in `logs/dashboard.log`.

**Not fixed, flagged only:** the identical `<AutoRefresh intervalSeconds={1} />` pattern is copy-pasted across 25 other dashboard pages (`payments`, `costs`, `tasks`, `sentinel`, `agents`, etc.). Most don't hit an expensive per-render external call the way the root page does, so they likely don't manifest the same symptom — not verified individually, out of scope for the one reported bug.

## Compute/infra state (verified live this session, not from memory)

- Linux GPU node `blackboxops@192.168.31.27` (`gvc-OPS-AI`, RTX 2050): reachable, GPU healthy (was found wedged in D-state earlier this session — a real `nvidia-persistenced` hang — founder ran `sudo systemctl restart nvidia-persistenced` to clear it).
- `OLLAMA_HOST` now points Mac tooling at the Linux box (`start_dashboard.sh` and `~/.zshrc`, both updated this session) instead of the Mac's local `Ollama.app`, per the standing GPU-first policy already documented in `AGENTS.md`'s "Compute preference" section.
- External SSD (`Shakthi_OS`-labeled, 223.6GB ext4) physically connected to the Linux box, kernel-detected, **not yet mounted** — no `/mnt/backup_ssd` mountpoint or fstab entry exists. First-time setup, needs `sudo` (commands already given to founder).

## Not yet reviewed (explicit unread areas — do not assume clean)

- `orchestrator/api.py`, `orchestrator/sentinel.py`, `orchestrator/pricing.py`, `orchestrator/db.py`, `db/schema.sql` — all currently dirty/modified, not diffed line-by-line yet.
- `dashboard/app/api/blackboxops/chat/route.ts`, `command-center/`, `org-chart/`, `voice/` — modified, not reviewed.
- `agents/*.yaml` (new, untracked), `orchestrator/security_policy.py`, `orchestrator/skills_library.py` (new, untracked, each with its own new test file) — not reviewed at all.
- `dhansetu-web/`, `data/`, `scripts/`, `linux_backup_before_wipe_20260913/` — untracked, contents unknown, not opened.
- No security-boundary review done yet (tool-access scoping, credential handling, insecure defaults) — Section 9/Guardian territory, not started.
- Sections 2–12 of the contract (framework selection, mission kernel, department contracts, token economics, revenue ledger, factories, watchdog, dashboard/mobile access) are **not started**. This is a multi-session build, not something to fabricate progress on.
