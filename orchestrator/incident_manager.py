"""
ERT -- Incident Manager. State machine + orchestration on top of
incident_registry.py (data) and ownership_engine.py (assignment
algorithm). Internal tracking only -- SQLite now, same "deliberate
Postgres stand-in" the rest of this project already uses (tenant_id
pattern doesn't apply here since incidents aren't per-business, but the
engine-swap path is the same: one choke point, db.py, same as everywhere
else in this codebase).
"""
import json
from datetime import datetime

from . import db, incident_registry, ownership_engine

STATE_ORDER = ["NEW", "ACKNOWLEDGED", "INVESTIGATING", "FIXING", "VERIFYING", "READY_TO_DEPLOY", "RESOLVED", "CLOSED"]


class IncidentError(RuntimeError):
    pass


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def create_incident(incident_type: str, description: str, detected_by: str = "manual",
                     telegram_token: str = None, telegram_chat_id: str = None) -> dict:
    with db.get_conn() as conn:
        assignment = ownership_engine.assign_owner(conn, incident_type)
        year = datetime.utcnow().year
        incident_number = db.next_incident_number(conn, year)
        incident_id = db.insert_incident(
            conn, incident_number, incident_type, assignment["severity"], assignment["owner"],
            json.dumps(assignment["support_team"]), description, detected_by=detected_by,
        )
        db.insert_incident_event(conn, incident_id, "created",
                                  f"type={incident_type} severity={assignment['severity']} owner={assignment['owner']} ({assignment['reason']})")
        if assignment["escalated"]:
            db.insert_incident_event(conn, incident_id, "escalated", assignment["reason"])

    result = {"incident_id": incident_id, "incident_number": incident_number, **assignment,
              "incident_type": incident_type, "description": description}

    _notify(result, telegram_token, telegram_chat_id)
    return result


def _notify(incident: dict, telegram_token: str, telegram_chat_id: str):
    severity = incident["severity"]
    notify_targets = incident_registry.SEVERITY_NOTIFY.get(severity, ["queue"])
    if notify_targets == ["queue"]:
        return  # P3/P4 -- tracked, not pushed, same "alert-only-when-it-matters" philosophy as alerts.py

    from . import telegram as tg
    from . import telegram_service as ts
    try:
        token, chat_id = ts.resolve_credentials(telegram_token, telegram_chat_id)
    except tg.TelegramError:
        return
    text = (f"🚨 SHAKTHI ERT — {incident['incident_number']}\n\n"
            f"Type: {incident['incident_type']}\n"
            f"Severity: {severity} ({incident_registry.SEVERITY_LABELS.get(severity, '')})\n"
            f"Owner: {incident['owner']}{' (ESCALATED)' if incident['escalated'] else ''}\n"
            f"Support: {', '.join(incident['support_team'])}\n\n"
            f"{incident['description']}")
    try:
        tg.send_message(token, chat_id, text, parse_mode=None)
    except tg.TelegramError:
        pass


def transition(incident_number: str, new_status: str, note: str = "") -> dict:
    if new_status not in STATE_ORDER:
        raise IncidentError(f"unknown status '{new_status}' — expected one of {STATE_ORDER}")
    with db.get_conn() as conn:
        incident = db.get_incident(conn, incident_number=incident_number)
        if not incident:
            raise IncidentError(f"no such incident: {incident_number}")
        current_idx, new_idx = STATE_ORDER.index(incident["status"]), STATE_ORDER.index(new_status)
        if new_idx <= current_idx:
            raise IncidentError(f"cannot move {incident_number} from {incident['status']} to {new_status} — forward-only state machine")
        db.update_incident_status(conn, incident["id"], new_status)
        db.insert_incident_event(conn, incident["id"], "state_change", f"{incident['status']} -> {new_status}. {note}".strip())
        return db.get_incident(conn, incident_id=incident["id"])


def resolve(incident_number: str, root_cause: str, fix_applied: str,
            recovery_action: str = None, recovery_result: str = None) -> dict:
    with db.get_conn() as conn:
        incident = db.get_incident(conn, incident_number=incident_number)
        if not incident:
            raise IncidentError(f"no such incident: {incident_number}")
        if STATE_ORDER.index(incident["status"]) >= STATE_ORDER.index("RESOLVED"):
            raise IncidentError(f"{incident_number} is already {incident['status']}")
        db.update_incident_fields(conn, incident["id"], root_cause=root_cause, fix_applied=fix_applied,
                                   recovery_action=recovery_action, recovery_result=recovery_result)
        db.update_incident_status(conn, incident["id"], "RESOLVED")
        db.insert_incident_event(conn, incident["id"], "state_change", f"{incident['status']} -> RESOLVED. root_cause={root_cause}")
        return db.get_incident(conn, incident_id=incident["id"])


def close(incident_number: str, generate_postmortem: bool = True) -> dict:
    with db.get_conn() as conn:
        incident = db.get_incident(conn, incident_number=incident_number)
        if not incident:
            raise IncidentError(f"no such incident: {incident_number}")
        if incident["status"] != "RESOLVED":
            raise IncidentError(f"{incident_number} must be RESOLVED before CLOSED (currently {incident['status']})")
        db.update_incident_status(conn, incident["id"], "CLOSED")
        db.insert_incident_event(conn, incident["id"], "state_change", "RESOLVED -> CLOSED")
        result = db.get_incident(conn, incident_id=incident["id"])

    if generate_postmortem:
        from . import incident_audit
        try:
            incident_audit.generate_postmortem(result["id"])
        except Exception as e:
            result["postmortem_error"] = str(e)
    return result


def mttr_seconds(conn, since_days: int = 30) -> float | None:
    """Mean time to resolution, real -- from created_at to resolved_at on
    actually-resolved incidents, not estimated."""
    rows = conn.execute(
        "SELECT created_at, resolved_at FROM incidents WHERE resolved_at IS NOT NULL "
        "AND created_at >= datetime('now', ?)", (f"-{since_days} days",),
    ).fetchall()
    if not rows:
        return None
    durations = []
    for r in rows:
        created = datetime.strptime(r["created_at"], "%Y-%m-%d %H:%M:%S")
        resolved = datetime.strptime(r["resolved_at"], "%Y-%m-%d %H:%M:%S")
        durations.append((resolved - created).total_seconds())
    return sum(durations) / len(durations)
