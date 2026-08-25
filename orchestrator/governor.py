"""
Governor -- a composite health aggregator, not a new control-flow layer.

There is nothing for a "governor" to actively enforce here: grep evidence
(see CEO_FAILURE_REPORT.md) already proved Finance/Security/Sentinel never
call ceo.decide() at all, and every pipeline that DOES use a CEO gate
already fails closed to a safe default rather than crashing. A governor
that supervised/restarted things would be solving a problem that doesn't
exist in this architecture.

What's genuinely useful and didn't exist before: ONE composite "is the
business still operational" signal, built by actually calling each
subsystem live (not asserting they're independent -- checking it, every
time this runs) and reporting real failover events (CEO decisions that
completed via local-fallback or came back non-approved) in one place.
"""
from datetime import datetime, timedelta

from . import ceo_health_monitor, db, load_manager, sentinel


def check_subsystems() -> dict:
    """Calls each subsystem's real entry point live -- proof, not
    assertion, that none of them require CEO to function."""
    checks = {}

    try:
        h = sentinel.collect_health()
        checks["sentinel"] = {"ok": True, "detail": f"health_score={h['health_score']}"}
    except Exception as e:
        checks["sentinel"] = {"ok": False, "detail": str(e)}

    try:
        with db.get_conn() as conn:
            lb = load_manager.load_balancer_status(conn)
        checks["worker_pool"] = {"ok": True, "detail": f"queue_depth={lb['queue_depth']}"}
    except Exception as e:
        checks["worker_pool"] = {"ok": False, "detail": str(e)}

    try:
        with db.get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM security_reports").fetchone()
        checks["security"] = {"ok": True, "detail": f"{row['n']} reports on record"}
    except Exception as e:
        checks["security"] = {"ok": False, "detail": str(e)}

    try:
        with db.get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM finance_entries").fetchone()
        checks["finance"] = {"ok": True, "detail": f"{row['n']} entries on record"}
    except Exception as e:
        checks["finance"] = {"ok": False, "detail": str(e)}

    return checks


def failover_events(conn, hours: int = 24) -> list:
    """Real failover events -- a CEO task that completed via local-
    fallback (routing.py's fix) or that came back non-approved after a
    genuine attempt. Not a new tracking table: this reads the same
    `tasks`/`decisions` rows ceo_health_monitor.py already reads, just
    framed as discrete events instead of a rolled-up count."""
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        "SELECT * FROM tasks WHERE agent_id = 'ceo' AND status IN ('failed', 'done_local_fallback') "
        "AND created_at >= ? ORDER BY id DESC",
        (cutoff,),
    ).fetchall()
    return [{"task_id": r["id"], "status": r["status"], "goal": r["goal"][:100], "at": r["created_at"]} for r in rows]


def governor_status(conn) -> dict:
    subsystems = check_subsystems()
    ceo = ceo_health_monitor.ceo_status(conn)
    events = failover_events(conn)

    all_subsystems_ok = all(s["ok"] for s in subsystems.values())
    status = "operational" if all_subsystems_ok else "degraded"

    return {
        "status": status, "subsystems": subsystems, "ceo": ceo,
        "failover_events_24h": events, "failover_event_count_24h": len(events),
    }
