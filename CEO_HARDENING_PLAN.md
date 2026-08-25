# CEO Hardening Plan

This consolidates what was separately requested as a Hardening Plan, an Isolation Plan, and a Fallback Implementation doc. They'd have been three copies of the same content viewed from different angles — Isolation and Fallback are both just "what happens when CEO fails," and Hardening is "what we did about it." Splitting that into three files would be padding, not more information, so it's one document that says what's real.

## Starting premise, checked against the code, not assumed

The request that prompted this asked for a "Router Kernel," "CEO Isolation," a "Fallback Router," and "Worker Dispatching" so that "if CEO crashes, Finance, Security, Sentinel, Website Builder, Chrome Developer, and Worker Pool must continue operating normally." That's the right goal. It just doesn't require new infrastructure to be true — it already is, and here's the evidence, not an assertion:

- `routing.run_task()` takes `agent_id` as a plain parameter. It dispatches identically for `security`, `sentinel`, `finance`, `chrome_developer`, `bug_fixer`, or `ceo` — there is no CEO-specific branch in the core dispatch path (confirmed by grep, zero matches, see CEO_FAILURE_REPORT.md §"What this is not").
- `security.security_posture_scan()`, `sentinel.collect_health()`, and `finance.generate_report()` contain **zero** references to `ceo` anywhere in their source. They cannot depend on something they never call.
- Every pipeline that *does* use a CEO gate (Correction Bot, Chrome Developer, Website Builder, the codebase Audit) already wraps that call in `try/except` and falls back to a safe, conservative default (`"revise"` / not-approved) rather than crashing. This was true before today's fix, too — it's why every one of this session's live runs completed, stored its result, and sent its Telegram report even on the two occasions CEO's gate failed.

So: a "Router Kernel" and a "Fallback Router" alongside the existing `routing.py` would be two files doing the same job, one of them redundant. That's the specific thing this plan avoids building, and why.

## What was actually broken, and what was fixed

See `CEO_FAILURE_REPORT.md` for the full analysis. In short: QA was reviewing CEO's own decisions as if they were proposed actions, rejecting valid "revise" outcomes, which forced a cloud-escalation attempt that discarded the real local decision when it failed. Two small, targeted changes to `orchestrator/routing.py` fixed both parts, live-verified against the exact failing case.

## What was built as real, new hardening (not redundant)

1. **`orchestrator/ceo_health_monitor.py`** — real telemetry: `ceo_status()` computes failure count, degraded count (local-fallback completions), last error, and recovery attempts from actual task history. Not simulated — pulled live and verified against real data (`failure_count: 4, recovery_attempts: 1` reflecting tasks #19/#20/#21 and earlier history).
2. **CEO-specific Telegram alerting** — `alerts.py` gained `check_ceo_failures`, wired into the *existing* sweep/dedup infrastructure every other alert category in this project already uses. Not a new notification mechanism — the same one, one more category.
3. **Dashboard telemetry** — `/ceo` now shows CEO Status, Failure Count, Degraded Count, Last Error, and Recovery Attempts, backed by a real `/api/ceo/health` endpoint.
4. **`_try_cloud()`'s local-fallback behavior** benefits every agent that goes through the QA→escalate path, not just CEO — Engineer, Bug Fixer, and anything else routed the same way now keeps its real local output when cloud escalation is unavailable, instead of losing it.

## What "CEO Fallback Mode" already means, concretely, today

- **If CEO fails:** the calling pipeline (Correction Bot / Chrome Developer / Website Builder / Audit) catches the exception, logs it via the existing `task_events`/`error_log` tables, defaults to the conservative outcome (not approved), and continues — verified live, repeatedly, this session.
- **Notify the founder:** `check_ceo_failures` → the existing Telegram sweep. Real, wired, using real credentials already proven this session.
- **"Use last known policies":** stated honestly — this project has no persisted "policy" concept to fall back to (no rules engine, no cached prior-decision-as-default mechanism). Building one would be new product design, not hardening, and wasn't asked for with enough specificity to build safely. If a real "same goal shape → reuse the last decision" cache is wanted, that's a scoped follow-up, not implied by "keep functioning" — I did not invent one to check a box.

## Deliberately not built, and why

- **Router Kernel / Fallback Router** — `routing.py` already is this. Renaming or duplicating it would add a second file to keep in sync for no behavior change.
- **CEO Isolation** (as a separate enforcement layer) — there was nothing to isolate; CEO was never structurally load-bearing for other agents' core operation. What needed isolating was CEO's *own* internal QA step from the rest of the QA pipeline, and that's what the routing.py fix does.
- **CEO Recovery Logic** as an active process (auto-retry, circuit breaker) — not built. The real failure mode was a logic bug, not transient unavailability; retrying the same buggy code path would have just failed the same way twice. Now that the bug is fixed, "recovery" is `ceo_health_monitor.py`'s `recovery_attempts` counter — observability, not an active retry loop that wasn't asked for with a concrete trigger condition.

## Verification

- `tests/test_routing_ceo_fix.py` — 4 new tests, full suite 214/214 passing.
- Live re-run of the exact scenario that produced failing task #20 → task #21, `status='done'`, real parseable decision, zero QA/escalation events.
- `ceo_health_monitor.ceo_status()` run against real `shakthi.db` data, confirmed correct output.
