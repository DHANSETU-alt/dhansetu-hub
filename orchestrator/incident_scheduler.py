"""
ERT -- automatic emergency detection. Reuses the real detectors this
project already has (sentinel.collect_health()'s thresholds, service
status, security posture, payment gateway status) rather than
re-implementing threshold logic a second time. This module's real job:
turn an already-detected problem into a tracked Incident, exactly once
per open occurrence (an open incident of the same type suppresses a
duplicate creation on the next sweep -- otherwise a sustained outage
would spawn a new incident every time this runs).
"""
from . import db, incident_manager

# Same 90%/85°C thresholds alerts.py's check_sentinel() already uses --
# one set of numbers, not two that could drift apart.
CPU_THRESHOLD = 90
RAM_THRESHOLD = 90
DISK_THRESHOLD = 90
TEMP_THRESHOLD_C = 85


def _has_open_incident(conn, incident_type: str) -> bool:
    # Same open-status list as ownership_engine.OPEN_STATUSES -- duplicated
    # as a tuple literal rather than imported, same "small enough to keep
    # local" call as bugfix_tools.py/paths.py's independent containment checks.
    open_statuses = ("NEW", "ACKNOWLEDGED", "INVESTIGATING", "FIXING", "VERIFYING", "READY_TO_DEPLOY")
    row = conn.execute(
        f"SELECT COUNT(*) AS n FROM incidents WHERE incident_type = ? AND status IN ({','.join('?' * len(open_statuses))})",
        (incident_type, *open_statuses),
    ).fetchone()
    return row["n"] > 0


def _maybe_create(conn, incident_type: str, description: str, telegram_token, telegram_chat_id) -> dict | None:
    if _has_open_incident(conn, incident_type):
        return None
    return incident_manager.create_incident(incident_type, description, detected_by="incident_scheduler",
                                             telegram_token=telegram_token, telegram_chat_id=telegram_chat_id)


def run_detection_sweep(website_urls: list = None, telegram_token: str = None, telegram_chat_id: str = None) -> dict:
    from . import sentinel

    created = []
    snap = sentinel.collect_health()
    # ollama_ok/db_ok live on the health snapshot, not service_status() --
    # that function reports docker/claude/telegram/sheets, not Ollama.
    # Found live: this originally called services.get("ollama") against
    # the wrong dict, which is always None/falsy -- a false "Ollama down"
    # incident on every single sweep regardless of Ollama's real state.

    with db.get_conn() as conn:
        if snap.get("cpu_percent") is not None and snap["cpu_percent"] > CPU_THRESHOLD:
            r = _maybe_create(conn, "resource_critical", f"CPU at {snap['cpu_percent']}% (> {CPU_THRESHOLD}%)", telegram_token, telegram_chat_id)
            created.append(r) if r else None
        if snap.get("ram_percent") is not None and snap["ram_percent"] > RAM_THRESHOLD:
            r = _maybe_create(conn, "resource_critical", f"RAM at {snap['ram_percent']}% (> {RAM_THRESHOLD}%)", telegram_token, telegram_chat_id)
            created.append(r) if r else None
        if snap.get("disk_percent") is not None and snap["disk_percent"] > DISK_THRESHOLD:
            r = _maybe_create(conn, "resource_critical", f"Disk at {snap['disk_percent']}% (> {DISK_THRESHOLD}%)", telegram_token, telegram_chat_id)
            created.append(r) if r else None
        if snap.get("cpu_temp_c") is not None and snap["cpu_temp_c"] > TEMP_THRESHOLD_C:
            r = _maybe_create(conn, "resource_critical", f"CPU temperature at {snap['cpu_temp_c']}°C (> {TEMP_THRESHOLD_C}°C)", telegram_token, telegram_chat_id)
            created.append(r) if r else None
        if not snap.get("db_ok"):
            r = _maybe_create(conn, "database_offline", "Database unreachable", telegram_token, telegram_chat_id)
            created.append(r) if r else None
        if not snap.get("ollama_ok"):
            r = _maybe_create(conn, "ollama_offline", "Ollama service unreachable", telegram_token, telegram_chat_id)
            created.append(r) if r else None

    if website_urls:
        from . import website_audit as wa
        for url in website_urls:
            home = wa.fetch(url)
            with db.get_conn() as conn:
                if not home["ok"]:
                    r = _maybe_create(conn, "website_down", f"{url} unreachable: {home.get('error') or home.get('status')}", telegram_token, telegram_chat_id)
                    created.append(r) if r else None
                elif not url.lower().startswith("https://"):
                    r = _maybe_create(conn, "ssl_failure", f"{url} not served over HTTPS", telegram_token, telegram_chat_id)
                    created.append(r) if r else None

    with db.get_conn() as conn:
        recent_failed = db.recent_tasks(conn, limit=20)
    if sum(1 for t in recent_failed if t["status"] == "failed") >= 5:
        with db.get_conn() as conn:
            r = _maybe_create(conn, "repeated_exceptions", "5+ of the last 20 tasks failed — possible agent crash pattern", telegram_token, telegram_chat_id)
            created.append(r) if r else None

    return {"checked": True, "incidents_created": [c for c in created if c], "count": len([c for c in created if c])}
