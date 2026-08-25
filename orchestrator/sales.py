"""
SHAKTHI SALES — real lead pipeline, not just a persona.

Root cause of "0 tasks ever routed to sales" (found by reading routing.py,
registry.py, and the agents table directly, not assumed): agents/sales.yaml
was correctly defined AND correctly registered (`registry.sync_registry()`
had already synced it into the `agents` table fine) AND routing.run_task()
is fully agent-agnostic — there is no special-casing anywhere that excludes
or blocks 'sales'. `--agent sales --goal "..."` would have worked from day
one. The real gap was upstream: nothing in this codebase ever CALLED it.
There was no lead-ingestion pipeline, no CRM event, nothing that would ever
generate a sales task in the first place. Missing pipeline, not a broken
router -- this module is that pipeline.

Every function here routes through routing.run_task("sales", ...), the
same real task/QA/cost-ledger/memory pipeline every other agent call in
this project uses -- not a parallel shortcut. That's what makes
`SELECT COUNT(*) FROM tasks WHERE agent_id='sales'` a real, falsifiable
proof rather than a claim: every call below leaves that row.

Connections are never nested (a real, previously-hit bug in this project:
two open `db.get_conn()` blocks deadlock SQLite with "database is locked")
-- every function here opens, reads/writes, and closes before calling
anything else that touches the database.
"""
import json
import re
from datetime import datetime

from . import db, routing

_SCORE_RE = re.compile(r"SCORE:\s*([01]?\.?\d+)", re.IGNORECASE)
_INTENT_RE = re.compile(r"INTENT:\s*([01]?\.?\d+)", re.IGNORECASE)
_REASON_RE = re.compile(r"REASON:\s*(.+)", re.IGNORECASE)

# Above this, a lead goes straight to the founder instead of getting an
# auto-drafted outreach message -- real negotiation/high-intent signals
# shouldn't get a templated reply.
ESCALATION_THRESHOLD = 0.7


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def _clamp01(raw: str):
    try:
        return max(0.0, min(1.0, float(raw)))
    except (TypeError, ValueError):
        return None


def _parse_score_output(text: str):
    """Fail-closed like the rest of this project's parsers: an unparseable
    field comes back as None, never a fabricated number."""
    score_m, intent_m, reason_m = _SCORE_RE.search(text), _INTENT_RE.search(text), _REASON_RE.search(text)
    score = _clamp01(score_m.group(1)) if score_m else None
    intent = _clamp01(intent_m.group(1)) if intent_m else None
    reason = reason_m.group(1).strip() if reason_m else "(model did not return a parseable reason)"
    return score, intent, reason


def score_lead(lead_id: int) -> dict:
    with db.get_conn() as conn:
        lead = db.get_lead(conn, lead_id)
    if not lead:
        raise ValueError(f"no lead #{lead_id}")

    goal = (
        "Score this inbound lead for fit/urgency and for negotiation/purchase intent.\n\n"
        f"Name: {lead['name']}\nEmail: {lead['email']}\nSource: {lead['source']}\n"
        f"Notes: {lead['notes'] or '(none)'}\n\n"
        "Respond with EXACTLY these three lines and nothing else:\n"
        "SCORE: <fit/urgency, 0.00-1.00>\n"
        "INTENT: <negotiation/purchase intent, 0.00-1.00>\n"
        "REASON: <one sentence>"
    )
    result = routing.run_task("sales", goal, business_id=lead["business_id"])
    score, intent, reason = _parse_score_output(result["output"])

    with db.get_conn() as conn:
        db.update_lead(conn, lead_id, score=score, score_reason=reason, status="scored")
        db.log_lead_event(conn, lead_id, "scored", json.dumps({"score": score, "intent": intent, "reason": reason}),
                           task_id=result["task_id"])

    return {"lead_id": lead_id, "task_id": result["task_id"], "score": score, "intent": intent,
            "reason": reason, "raw": result["output"]}


def draft_outreach(lead_id: int) -> dict:
    with db.get_conn() as conn:
        lead = db.get_lead(conn, lead_id)
    if not lead:
        raise ValueError(f"no lead #{lead_id}")

    goal = (
        "Draft a short, real cold/warm outreach email to this lead. Never invent pricing, "
        "discounts, or commitments not given below -- flag anything you'd need as a question "
        "for the founder instead of guessing.\n\n"
        f"Name: {lead['name']}\nEmail: {lead['email']}\nSource: {lead['source']}\n"
        f"Notes: {lead['notes'] or '(none)'}\nFit score: {lead['score']}\n\n"
        "Write the email only -- a subject line, then the body."
    )
    result = routing.run_task("sales", goal, business_id=lead["business_id"])

    with db.get_conn() as conn:
        db.update_lead(conn, lead_id, status="contacted", next_action="awaiting reply", last_contact_at=_now())
        db.log_lead_event(conn, lead_id, "outreach_drafted", json.dumps({"task_id": result["task_id"]}),
                           task_id=result["task_id"])

    return {"lead_id": lead_id, "task_id": result["task_id"], "status": result["status"], "draft": result["output"]}


def draft_proposal(lead_id: int, deal_context: str = "") -> dict:
    with db.get_conn() as conn:
        lead = db.get_lead(conn, lead_id)
    if not lead:
        raise ValueError(f"no lead #{lead_id}")

    goal = (
        "Draft a proposal/quote for this lead. Never invent pricing, discounts, or contract "
        "terms not given below -- flag those as questions for the founder instead of guessing.\n\n"
        f"Name: {lead['name']}\nEmail: {lead['email']}\nFit score: {lead['score']}\n"
        f"Deal context: {deal_context or '(none provided)'}\n\n"
        "Write the proposal only."
    )
    # classify_risk() already flags 'contract'/'custom pricing' language as
    # critical -- a real proposal naturally routes through the founder-review
    # path on its own when deal_context actually contains those terms.
    result = routing.run_task("sales", goal, business_id=lead["business_id"])

    with db.get_conn() as conn:
        db.log_lead_event(conn, lead_id, "proposal_drafted", json.dumps({"task_id": result["task_id"]}),
                           task_id=result["task_id"])

    return {"lead_id": lead_id, "task_id": result["task_id"], "status": result["status"], "draft": result["output"]}


def flag_for_founder(lead_id: int, reason: str, telegram_token: str = None, telegram_chat_id: str = None) -> dict:
    with db.get_conn() as conn:
        lead = db.get_lead(conn, lead_id)
    if not lead:
        raise ValueError(f"no lead #{lead_id}")

    goal = f"Escalation: lead '{lead['name']}' ({lead['email']}) flagged for founder review. Reason: {reason}"
    # force_risk="critical" is the same field routing.run_task() already
    # exposes for exactly this -- reused, not a parallel escalation path.
    result = routing.run_task("sales", goal, business_id=lead["business_id"], force_risk="critical")

    with db.get_conn() as conn:
        db.update_lead(conn, lead_id, owner="founder", status="negotiating", next_action="founder review required")
        db.log_lead_event(conn, lead_id, "escalated", json.dumps({"reason": reason}), task_id=result["task_id"])

    if telegram_token and telegram_chat_id:
        from . import telegram
        try:
            telegram.send_message(
                telegram_token, telegram_chat_id,
                f"High-intent lead needs you: {lead['name']} ({lead['email']}) — {reason}",
                parse_mode=None,
            )
        except telegram.TelegramError:
            pass  # best-effort -- the lead is already flagged in-app regardless

    return {"lead_id": lead_id, "task_id": result["task_id"], "status": result["status"]}


def ingest_lead(business_id, name: str, email: str, source: str, contact: str = None,
                 notes: str = None, telegram_token: str = None, telegram_chat_id: str = None) -> dict:
    """The real trigger point: any new lead / inbound / CRM event calls
    this. Auto-routes to the sales agent for scoring, then either drafts
    outreach or escalates to the founder, per ESCALATION_THRESHOLD."""
    with db.get_conn() as conn:
        lead_id = db.insert_lead(conn, business_id, name, email, contact, source, notes)

    scored = score_lead(lead_id)

    if scored["intent"] is not None and scored["intent"] > ESCALATION_THRESHOLD:
        detail = flag_for_founder(lead_id, f"negotiation/purchase intent {scored['intent']:.2f} at intake",
                                   telegram_token=telegram_token, telegram_chat_id=telegram_chat_id)
        return {"lead_id": lead_id, "action": "escalated_to_founder", "scored": scored, "detail": detail}

    detail = draft_outreach(lead_id)
    return {"lead_id": lead_id, "action": "outreach_drafted", "scored": scored, "detail": detail}
