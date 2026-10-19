"""
SHAKTHI CLIENT SUCCESS — real health tracking for won leads, not just a
persona. Root cause of "no client success anywhere" (found by reading the
`agents` table and routing.py directly): the `customer_success` agent row
was already registered and already reachable via routing.run_task() --
routing.py is fully agent-agnostic, same as it was for sales -- but nothing
in this codebase ever called it. No health signal, no renewal check,
nothing that would ever generate a customer_success task. Missing
pipeline, not a broken router -- this module is that pipeline, structured
exactly like sales.py.

A "client" is a lead with status='won' -- no separate clients table, reuse
what exists. Health is computed from product_usage and
product_subscriptions (both keyed by email, per db/schema.sql's own
comment: "email is the only identity concept this project has for paying
customers"), never fabricated when a lead has no usage/subscription row at
all -- see compute_health_score()'s docstring.

Every action that writes a task routes through
routing.run_task("customer_success", ...), the same real
task/QA/cost-ledger/memory pipeline every other agent call in this project
uses. Connections are never nested (the documented SQLite "database is
locked" deadlock rule from sales.py) -- every function here opens,
reads/writes, and closes before calling anything else that touches the
database.
"""
import json
from datetime import datetime

from . import db, routing

# Below this, a client is flagged at-risk instead of assumed healthy --
# first-pass weights (see compute_health_score), tunable once there's
# enough real client history to calibrate against.
AT_RISK_THRESHOLD = 40


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def _days_since(timestamp: str | None) -> float | None:
    if not timestamp:
        return None
    try:
        then = datetime.strptime(timestamp.split(".")[0], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return (datetime.utcnow() - then).total_seconds() / 86400


def compute_health_score(lead_id: int) -> dict:
    """Pure function, no DB writes. Reads product_usage/product_subscriptions
    for this lead's email and scores 0-100. A lead with no usage and no
    subscription at all (e.g. won but never actually onboarded) scores 0
    with signals={} rather than being skipped -- that's a real, visible
    at-risk condition, not a data gap to hide."""
    with db.get_conn() as conn:
        lead = db.get_lead(conn, lead_id)
        if not lead:
            raise ValueError(f"no lead #{lead_id}")
        usage_rows = conn.execute(
            "SELECT * FROM product_usage WHERE email = ?", (lead["email"],)
        ).fetchall()
        sub_rows = conn.execute(
            "SELECT * FROM product_subscriptions WHERE email = ? ORDER BY id DESC", (lead["email"],)
        ).fetchall()
    usage_rows = [dict(r) for r in usage_rows]
    sub_rows = [dict(r) for r in sub_rows]

    score = 0
    signals = {}

    if usage_rows:
        last_used = min((_days_since(r["last_used_at"]) for r in usage_rows if r["last_used_at"]), default=None)
        use_count = sum(r["use_count"] for r in usage_rows)
        signals["days_since_last_use"] = last_used
        signals["total_use_count"] = use_count
        if last_used is not None:
            if last_used <= 7:
                score += 50
            elif last_used <= 30:
                score += 30
            elif last_used <= 90:
                score += 10
        score += min(20, use_count)  # frequency, capped

    active_sub = next((r for r in sub_rows if r["status"] == "active"), None)
    if active_sub:
        signals["subscription_status"] = "active"
        until = _days_since(active_sub["valid_until"])
        signals["days_until_expiry"] = -until if until is not None else None  # negative = days remaining
        if until is not None and until < 0:
            score += 30  # still within its validity window
        elif until is not None and until <= 7:
            score += 15  # expired within the last week -- grace period, not yet a full drop
    elif sub_rows:
        signals["subscription_status"] = sub_rows[0]["status"]

    return {"lead_id": lead_id, "score": max(0, min(100, score)), "signals": signals}


def score_client_health(lead_id: int) -> dict:
    computed = compute_health_score(lead_id)
    with db.get_conn() as conn:
        lead = db.get_lead(conn, lead_id)
        db.insert_client_health_score(conn, lead_id, lead["business_id"] if lead else None,
                                       computed["score"], json.dumps(computed["signals"]))
        db.log_client_health_event(conn, lead_id, "health_scored", json.dumps(computed))
    return computed


def flag_at_risk(lead_id: int, reason: str, telegram_token: str = None, telegram_chat_id: str = None) -> dict:
    with db.get_conn() as conn:
        lead = db.get_lead(conn, lead_id)
    if not lead:
        raise ValueError(f"no lead #{lead_id}")

    goal = f"At-risk client: '{lead['name']}' ({lead['email']}) flagged for retention review. Reason: {reason}"
    # force_risk="critical" is the same field routing.run_task() already
    # exposes for exactly this -- reused, not a parallel escalation path.
    result = routing.run_task("customer_success", goal, business_id=lead["business_id"], force_risk="critical")

    with db.get_conn() as conn:
        db.log_client_health_event(conn, lead_id, "at_risk_flagged", json.dumps({"reason": reason}),
                                    task_id=result["task_id"])

    if telegram_token and telegram_chat_id:
        from . import telegram
        try:
            telegram.send_message(
                telegram_token, telegram_chat_id,
                telegram.escape_markdown_v2(f"At-risk client needs you: {lead['name']} ({lead['email']}) — {reason}"),
            )
        except telegram.TelegramError:
            pass  # best-effort -- already flagged in-app regardless

    return {"lead_id": lead_id, "task_id": result["task_id"], "status": result["status"]}


def draft_retention_outreach(lead_id: int) -> dict:
    with db.get_conn() as conn:
        lead = db.get_lead(conn, lead_id)
        health = db.latest_client_health_score(conn, lead_id)
    if not lead:
        raise ValueError(f"no lead #{lead_id}")

    goal = (
        "Draft a short, real retention/check-in email to this at-risk client. Never invent "
        "discounts, extensions, or commitments not given below -- flag anything you'd need as "
        "a question for the founder instead of guessing.\n\n"
        f"Name: {lead['name']}\nEmail: {lead['email']}\n"
        f"Health score: {health['score'] if health else 'not yet scored'}/100\n\n"
        "Write the email only -- a subject line, then the body."
    )
    result = routing.run_task("customer_success", goal, business_id=lead["business_id"])

    with db.get_conn() as conn:
        db.log_client_health_event(conn, lead_id, "retention_outreach_drafted", json.dumps({"task_id": result["task_id"]}),
                                    task_id=result["task_id"])

    return {"lead_id": lead_id, "task_id": result["task_id"], "status": result["status"], "draft": result["output"]}


def scan_all_clients() -> list[dict]:
    """The cron producer: score every won lead. Analog of
    security.security_posture_scan() -- something (--client-health-scan or
    a cron entry) must call this for client_health_scores to have fresh
    rows; the alert-check below only reads the latest ones, it doesn't
    collect."""
    with db.get_conn() as conn:
        clients = db.list_leads(conn, status="won", limit=1000)
    return [score_client_health(c["id"]) for c in clients]
