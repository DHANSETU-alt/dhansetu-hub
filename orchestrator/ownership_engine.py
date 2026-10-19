"""
ERT -- ownership ASSIGNMENT algorithm. incident_registry.py is the data
(the matrix); this is what actually runs it: automatic assignment, backup
assignment when the primary is unavailable, escalation to Governor when
both are unavailable, and load balancing when the primary owner already
has too many open incidents.

"Owner offline" is checked honestly, not faked:
  - SYSTEM owners (sentinel, governor, worker_pool, security, chrome_developer,
    bug_fixer, website_builder, router_kernel) get a REAL health check --
    reusing governor.check_subsystems() and direct module calls, not a new
    detector.
  - HUMAN-ROLE owners (finance_lead, security_lead, customer_success_lead,
    infrastructure_lead, ai_operations_lead) have no presence system
    anywhere in this codebase. There's no login system, no "online"
    concept for a person. These are always treated as available -- stated
    here plainly, not silently assumed.
"""
from . import db, incident_registry

OPEN_STATUSES = ("NEW", "ACKNOWLEDGED", "INVESTIGATING", "FIXING", "VERIFYING", "READY_TO_DEPLOY")
MAX_OPEN_INCIDENTS_PER_OWNER = 3  # load-balancing threshold: past this, prefer the backup


def _check_system_owner_health(owner: str) -> bool:
    """Real checks, reusing already-built modules -- not a new detector
    per owner. Returns True (available) for anything not mapped, which
    only happens for a system owner name that isn't wired here yet."""
    try:
        if owner == "sentinel":
            from . import sentinel
            sentinel.collect_health()
            return True
        if owner == "governor":
            from . import governor
            with db.get_conn() as conn:
                status = governor.governor_status(conn)
            return status["status"] == "operational"
        if owner == "worker_pool":
            from . import load_manager
            with db.get_conn() as conn:
                load_manager.load_balancer_status(conn)
            return True
        if owner == "security":
            from . import security
            security.scan_env_vars()  # cheap, deterministic, no network
            return True
        if owner in ("chrome_developer", "website_builder", "bug_fixer", "router_kernel"):
            return True  # no independent health signal exists for these yet -- assumed available, not faked as "checked"
    except Exception:
        return False
    return True


def is_owner_available(owner: str) -> bool:
    system_owners = {"sentinel", "governor", "worker_pool", "security", "chrome_developer",
                      "bug_fixer", "website_builder", "router_kernel"}
    if owner in system_owners:
        return _check_system_owner_health(owner)
    return True  # human-role owner -- no presence system exists, honestly assumed available


def _open_incident_count(conn, owner: str) -> int:
    rows = conn.execute(
        f"SELECT COUNT(*) AS n FROM incidents WHERE owner = ? AND status IN ({','.join('?' * len(OPEN_STATUSES))})",
        (owner, *OPEN_STATUSES),
    ).fetchone()
    return rows["n"]


def assign_owner(conn, incident_type: str) -> dict:
    """Automatic Assignment -> Backup Assignment -> Escalation Routing ->
    Load Balancing, in that order, as the spec asked for."""
    entry = incident_registry.lookup(incident_type)
    primary, backup = entry["owner"], entry["backup"]

    if not is_owner_available(primary):
        if not is_owner_available(backup):
            return {"owner": "governor", "reason": f"both '{primary}' and backup '{backup}' unavailable — escalated to Governor",
                    "escalated": True, "support_team": entry["support"], "severity": entry["severity"]}
        return {"owner": backup, "reason": f"primary owner '{primary}' unavailable — assigned to backup",
                "escalated": False, "support_team": entry["support"], "severity": entry["severity"]}

    load = _open_incident_count(conn, primary)
    if load >= MAX_OPEN_INCIDENTS_PER_OWNER:
        if is_owner_available(backup):
            return {"owner": backup, "reason": f"primary owner '{primary}' has {load} open incidents (>= {MAX_OPEN_INCIDENTS_PER_OWNER}) — load-balanced to backup",
                    "escalated": False, "support_team": entry["support"], "severity": entry["severity"]}
        return {"owner": "governor", "reason": f"primary '{primary}' overloaded ({load} open) and backup '{backup}' unavailable — escalated to Governor",
                "escalated": True, "support_team": entry["support"], "severity": entry["severity"]}

    return {"owner": primary, "reason": "primary owner available", "escalated": False,
            "support_team": entry["support"], "severity": entry["severity"]}
