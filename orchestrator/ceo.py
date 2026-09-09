"""
CEO decision workflow. Routed local-first like every other agent (Ollama
default, Claude only via the same critical/QA-fail escalation path
routing.py already uses) -- the founder's own restated requirement for this
phase overrides the v1 architecture doc's "Executive layer defaults to
Claude" framing. A decision that's actually critical (money, customer data,
legal, production) gets there anyway through classify_risk(), same as any
other task.
"""
import json
import re

from . import db, routing

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


class DecisionParseError(RuntimeError):
    pass


def _parse_decision(text: str) -> dict:
    match = None
    for match in _FENCE_RE.finditer(text):
        pass
    if not match:
        raise DecisionParseError(f"CEO agent did not return a parseable decision block: {text!r}")
    data = json.loads(match.group(1))
    for field in ("status", "priority_score", "risk_score", "business_impact_score"):
        if field not in data:
            raise DecisionParseError(f"decision missing required field {field!r}: {data!r}")
    return data


def decide(goal: str, business_id: int | None = None, agent_id: str = "ceo") -> dict:
    """agent_id defaults to 'ceo' (Team 1) -- every existing caller keeps
    working unchanged. Real gap found + fixed 2026-09-09: this was
    hardcoded to "ceo" literally, which made Team 2's ceo_2 (created same
    session) unreachable through any real code path -- present in the
    registry as data, but nothing could ever actually dispatch to it.
    Root cause (5-Why/KPIV, per founder's own requested method): the
    entry point had the target agent baked in as a literal instead of a
    parameter. Pass agent_id='ceo_2' to route to Team 2 instead."""
    result = routing.run_task(agent_id, goal, business_id=business_id)

    try:
        parsed = _parse_decision(result["output"])
    except (DecisionParseError, json.JSONDecodeError) as e:
        # Fail loud, not silent -- a mis-parsed decision must not be
        # mistaken for an approved one.
        parsed = {
            "status": "revise",
            "priority_score": None,
            "risk_score": None,
            "business_impact_score": None,
            "reason": f"could not parse CEO output, defaulting to 'revise': {e}",
        }

    with db.get_conn() as conn:
        decision_id = db.insert_decision(
            conn,
            task_id=result["task_id"],
            business_id=business_id,
            goal=goal,
            status=parsed["status"],
            priority_score=parsed.get("priority_score"),
            risk_score=parsed.get("risk_score"),
            business_impact_score=parsed.get("business_impact_score"),
            reason=parsed.get("reason", ""),
        )

    return {"decision_id": decision_id, **parsed, "task_id": result["task_id"]}
