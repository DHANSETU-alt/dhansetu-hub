"""
CEO Health Monitor -- real telemetry on the `ceo` agent's task history.
No new alerting mechanism: Telegram notification reuses alerts.py's
existing CHECKS registry (see check_ceo_failures there), the same
cursor-dedup pattern every other alert category in this project uses.

Scope, stated plainly: with routing.py's fix (ceo is now QA-exempt for
normal-risk goals, and _try_cloud falls back to the real local output
instead of discarding it), a CEO failure should now be rare -- it can
still happen for a genuinely `critical`-risk goal (classify_risk()) that
needs real cloud escalation and ANTHROPIC_API_KEY isn't set. This module
tracks that real remaining failure mode, not a hypothetical one.
"""
from . import db

# "done_local_fallback" (routing.py's new status) counts as degraded, not
# failed -- the decision DID complete, just without cloud confirmation.
DEGRADED_STATUSES = ("done_local_fallback",)
FAILED_STATUSES = ("failed",)


def ceo_tasks(conn, limit: int = 200) -> list:
    rows = conn.execute(
        "SELECT * FROM tasks WHERE agent_id = 'ceo' ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def ceo_status(conn) -> dict:
    tasks = ceo_tasks(conn, limit=50)
    if not tasks:
        return {"status": "unknown", "failure_count": 0, "degraded_count": 0, "last_error": None,
                "recovery_attempts": 0, "total_tracked": 0}

    failures = [t for t in tasks if t["status"] in FAILED_STATUSES]
    degraded = [t for t in tasks if t["status"] in DEGRADED_STATUSES]

    # Recovery attempt: a CEO task that succeeded (status='done') with an
    # earlier-id CEO task in this window having failed -- a real "it came
    # back" signal, not just a raw success count.
    recovery_attempts = 0
    seen_failure = False
    for t in reversed(tasks):  # oldest -> newest
        if t["status"] in FAILED_STATUSES:
            seen_failure = True
        elif t["status"] == "done" and seen_failure:
            recovery_attempts += 1
            seen_failure = False

    recent = tasks[:10]
    recent_failed = sum(1 for t in recent if t["status"] in FAILED_STATUSES)
    if recent_failed >= len(recent) and recent:
        status = "down"
    elif failures or degraded:
        status = "degraded"
    else:
        status = "healthy"

    last_error = None
    if failures:
        last_error = {"task_id": failures[0]["id"], "goal": failures[0]["goal"][:100],
                       "result": (failures[0]["result"] or "")[:300], "at": failures[0]["created_at"]}

    return {
        "status": status, "failure_count": len(failures), "degraded_count": len(degraded),
        "last_error": last_error, "recovery_attempts": recovery_attempts, "total_tracked": len(tasks),
    }
