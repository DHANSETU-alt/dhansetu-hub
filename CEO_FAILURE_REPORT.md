# CEO Failure Report

Root cause analysis for CEO tasks #19 and #20, both reported as `status='failed'`. Every fact below is pulled directly from `shakthi.db` (`tasks`, `task_events`, `decisions`) — not reconstructed from memory or assumed.

## 1. Why tasks #19 and #20 failed

**They did not fail because CEO is unreliable, crashed, or is architecturally fragile.** They failed because of two compounding bugs, both now fixed and live-verified:

1. **QA was rejecting CEO's own legitimate decisions.** `routing.run_task()` runs every non-critical-risk agent output through a QA validation step before accepting it. CEO was never exempted from this (unlike `qa`/`memory`, which already were). QA's job — per its own role prompt — is to catch "unmet requirements, obvious bugs, unhandled edge cases, unsafe or destructive actions" in a *proposed action*. A CEO decision isn't a proposed action; it's a judgment call, and "revise" is just as legitimate an outcome as "approve." QA treated CEO's reasoned "revise" as if declining to approve were itself the bug, and rejected it.
2. **A QA rejection forced an escalation attempt to Claude, which discarded the real decision.** Once QA said FAIL, `routing.py` tried `_try_cloud()`. That failed immediately — `ANTHROPIC_API_KEY` is not set this session, by deliberate policy ("the system will not silently spend money"). The bug: `_try_cloud()`'s failure path returned only a generic `"[escalation unavailable...]"` string — it never had access to gemma4's actual, real, well-formed decision to fall back to. That real decision was silently discarded, and `ceo.decide()` then failed to parse the placeholder string, defaulting to `status: "revise"` with a generic, unhelpful reason.

**The missing `ANTHROPIC_API_KEY` is a real, intentional constraint, not itself a bug** — every escalation path in this project fails loudly rather than silently spending money, and this has been true and documented all session. What was a real bug: QA misapplying its check to a decision task in the first place, and the local model's real output being thrown away once that triggered an escalation that couldn't complete.

## 2. Exact error

Task #19:
```
[escalation unavailable, returning best local effort: Cloud escalation requested
but ANTHROPIC_API_KEY is not set. This is intentional — the system will not
silently spend money.]
```
Task #20: identical error text.

## 3. "Stack trace" — the real event sequence (from `task_events`, both tasks identical in shape)

```
dispatch            {"risk": "normal", "agent": "ceo"}
validate_fail       FAIL — Reason: The agent's output does not meet the task goal
                    as it suggests revising the report instead of approving the
                    correction.                                    [task #19]

                    FAIL — Reason: ... does not consider revising the application
                    to address this issue ... incomplete review of the task's
                    readiness for deployment.                      [task #20]
escalate            routing to Claude
escalation_unavailable   Cloud escalation requested but ANTHROPIC_API_KEY is not set.
```
No Python exception, no traceback in the usual sense — `error_log` has zero rows in this window. This was a caught, handled, logged condition throughout; the system never crashed. `ceo.decide()`'s own `try/except DecisionParseError` caught the unparseable placeholder and produced a safe `"revise"` default rather than a silent approval — the fail-closed design worked correctly even while the underlying bug was active.

## 4. Affected files

- `orchestrator/routing.py` — `run_task()` (QA exemption list), `_try_cloud()` (discarded local fallback)
- `orchestrator/ceo.py` — `decide()`, `_parse_decision()` (downstream victim: correctly fails closed, but had nothing real to parse)

## 5. Affected functions

- `routing.run_task()` — line ~57 in the pre-fix version: `if agent_id in ("qa", "memory"):` — missing `"ceo"`
- `routing._validate()` — unaffected itself, but applied where it shouldn't have been
- `routing._try_cloud()` — signature had no way to receive or return the local model's real output
- `ceo.decide()` / `ceo._parse_decision()` — correctly fail-closed on the corrupted input they were given

## 6. Affected dependencies

None external. This was pure internal control flow — `model_gateway.call_local()` (gemma4) and the `qa` agent (llama3.2) both worked correctly and returned real output; the bug was in how `routing.py` combined and handled their results, not in any model or API call itself. `model_gateway.call_cloud()` correctly raised `ModelError` exactly as designed when no key is configured.

## What this is not

Worth stating precisely, since the request that triggered this report used "single point of failure" framing: **grep evidence, not assertion** —

```
$ grep -n '"ceo"' orchestrator/routing.py          # (before the fix) → no matches
$ grep -n "ceo\." orchestrator/security.py orchestrator/sentinel.py orchestrator/finance.py
                                                     → no matches in any of the three
```

`routing.py` was already fully agent-agnostic before this fix — it has never special-cased CEO, and Finance/Security/Sentinel's core operations (`security_posture_scan`, `collect_health`, `generate_report`) never call `ceo.decide()` at all. When CEO's internal gate inside Correction Bot / Chrome Developer / Website Builder declined (fail-closed), those pipelines completed anyway — every live run this session stored its result and sent its Telegram report regardless of the CEO gate's outcome. The system was never down; one specific decision-quality path had a real, now-fixed bug.

## Fix, applied and live-verified

Both changes are in `orchestrator/routing.py`:
1. `run_task()`: `ceo` added to the QA-exemption list, next to `qa`/`memory`.
2. `_try_cloud()`: accepts `local_fallback_text`; when cloud escalation is unavailable, falls back to the real local output (tagged with a note that cloud confirmation wasn't available) instead of discarding it.

4 new tests (`tests/test_routing_ceo_fix.py`), full suite 214/214 passing. **Live-verified**, not just unit-tested: re-ran the exact same Chrome Developer review that produced failing task #20 —

```
task #21: status = 'done' (was 'failed')
result   = real, parseable JSON: {"status": "revise", "priority_score": 9,
           "risk_score": 9, "business_impact_score": 5, "reason": "..."}
events   = dispatch only — no validate_fail, no escalate, no escalation_unavailable
```

One separate, honest observation from that same live run, unrelated to this bug: gemma4's stated reasoning referenced "ANTHROPIC_API_KEY" as if that were the website's problem, when the actual finding was "no clear call-to-action." That's a local-model reasoning-quality issue, not something this fix caused or was asked to address — noted for awareness, not treated as in-scope here.
