"""
Alert sweep. This is now the ONLY thing the scheduled/automated Telegram
path sends -- full report text goes to Google Sheets, not chat. Six
categories, matching exactly what was asked for: revenue, new orders
(treated as the same signal as revenue -- this system has no separate
"order" entity, just finance_entries), security, website downtime, agent
failures, critical CEO decisions.

State (.alerts_sync_state.json) tracks the last-seen id per category so a
sweep only alerts on what's NEW since the previous run -- otherwise every
cron tick would re-send the same alerts forever.

`telegram_service.send_report`/`--telegram-send` remain available for a
founder to pull a full report on demand -- that's a person asking for
something, not the automated path pushing one. See README for the
distinction.
"""
import json
from pathlib import Path

from . import config, db
from . import telegram as tg
from . import telegram_service as ts

STATE_PATH = config.ROOT / ".alerts_sync_state.json"


def _load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def _save_state(state: dict):
    STATE_PATH.write_text(json.dumps(state, indent=2))


def mark_revenue_seen(entry_id: int):
    """Called by cli._cmd_finance_entry right after it sends its own
    immediate revenue alert, so the next --alerts-sweep doesn't re-alert on
    the same entry. Without this, an interactively-logged revenue entry
    gets notified twice: once immediately, once again on the next sweep --
    found live, not hypothetical, testing this against a real chat."""
    state = _load_state()
    state["revenue_last_id"] = max(state.get("revenue_last_id", 0), entry_id)
    _save_state(state)


def check_revenue(conn, state: dict) -> list:
    entries = db.list_finance_entries(conn, since_id=state.get("revenue_last_id", 0), type_="revenue")
    if entries:
        state["revenue_last_id"] = max(e["id"] for e in entries)
    businesses = {b["id"]: b["name"] for b in db.list_businesses(conn)}
    return [f"New revenue: ${e['amount']:.2f} — {businesses.get(e['business_id'], '?')} ({e['description']})" for e in entries]


def check_security(conn, state: dict) -> list:
    rows = db.recent_tool_calls(conn, limit=50, decision="denied")
    new = [r for r in rows if r["id"] > state.get("security_last_denied_id", 0)]
    if rows:
        state["security_last_denied_id"] = max(r["id"] for r in rows)
    return [f"Permission denied: agent '{r['agent_id']}' tried '{r['tool_name']}' — {r['denial_reason']}" for r in new]


def check_website_downtime(conn, state: dict) -> list:
    sites = conn.execute("SELECT * FROM sites WHERE status != 'planned'").fetchall()
    messages = []
    known_down = set(state.get("sites_down", []))
    still_down = set()
    for s in sites:
        exists = bool(s["local_path"] and Path(s["local_path"]).exists())
        if not exists:
            still_down.add(s["id"])
            if s["id"] not in known_down:
                messages.append(f"Site file missing: {s['domain']} (business {s['business_id']})")
    state["sites_down"] = list(still_down)
    return messages


def check_agent_failures(conn, state: dict) -> list:
    tasks = db.recent_tasks(conn, limit=100)
    new_failed = [t for t in tasks if t["status"] == "failed" and t["id"] > state.get("failures_last_id", 0)]
    if tasks:
        state["failures_last_id"] = max(t["id"] for t in tasks)
    return [f"Task #{t['id']} failed: agent '{t['agent_id']}' (risk={t['risk_level']})" for t in new_failed]


def check_critical_ceo_decisions(conn, state: dict) -> list:
    decisions = db.decisions_since(conn, since_id=state.get("ceo_alert_last_id", 0))
    if decisions:
        state["ceo_alert_last_id"] = max(d["id"] for d in decisions)
    critical = [d for d in decisions if d["status"] in ("rejected", "revise") or (d["risk_score"] or 0) >= 7]
    return [f"CEO decision #{d['id']} [{d['status']}] risk={d['risk_score']}: {d['goal'][:60]}" for d in critical]


def check_critical_bugs(conn, state: dict) -> list:
    """P0/P1 bugs, from any source (manual, scan, or an audit run) --
    Phase 0.4's Bug Fixer alert category."""
    bugs = db.bugs_since(conn, since_id=state.get("bugs_alert_last_id", 0), severity_in=("P0", "P1"))
    all_recent = db.list_bugs(conn, limit=100)
    if all_recent:
        state["bugs_alert_last_id"] = max(state.get("bugs_alert_last_id", 0), max(b["id"] for b in all_recent))
    return [f"Bug #{b['id']} [{b['severity']}]: {b['title'][:70]}" for b in bugs]


def check_audit_critical_findings(conn, state: dict) -> list:
    """Raw audit findings at P0 or in the security category -- covers
    findings an audit surfaced but didn't deepen into a full bug (only the
    top few per run get deepened; this way a P0 finding #40 out of 54
    still gets seen, not just the ones that happened to rank in the top 3)."""
    rows = conn.execute(
        "SELECT * FROM audit_findings WHERE id > ? AND (severity = 'P0' OR category = 'security') ORDER BY id",
        (state.get("audit_finding_alert_last_id", 0),),
    ).fetchall()
    rows = [dict(r) for r in rows]
    if rows:
        state["audit_finding_alert_last_id"] = max(r["id"] for r in rows)
    return [f"Audit #{r['audit_id']} finding [{r['severity']}/{r['category']}]: {r['description'][:70]} ({r['file_path']})"
            for r in rows]


def check_fix_completed(conn, state: dict) -> list:
    """Bugs that reached fix_applied since last check -- 'fix completed'."""
    rows = conn.execute(
        "SELECT * FROM bugs WHERE id > ? AND status IN ('fix_applied', 'verified') ORDER BY id",
        (state.get("fix_completed_last_id", 0),),
    ).fetchall()
    rows = [dict(r) for r in rows]
    if rows:
        state["fix_completed_last_id"] = max(r["id"] for r in rows)
    return [f"Fix applied: bug #{r['id']} [{r['status']}] {r['title'][:60]}" for r in rows]


def check_voice_denied(conn, state: dict) -> list:
    """A voice command that was denied -- insufficient permission, or CEO
    didn't approve a risky one. Security-relevant: someone (a guest voice,
    or a family voice reaching for something restricted) tried and was
    correctly refused -- worth knowing about, not worth a full report."""
    rows = conn.execute(
        "SELECT * FROM voice_commands WHERE id > ? AND denied_reason IS NOT NULL ORDER BY id",
        (state.get("voice_denied_last_id", 0),),
    ).fetchall()
    rows = [dict(r) for r in rows]
    if rows:
        state["voice_denied_last_id"] = max(r["id"] for r in rows)
    return [f"Voice command denied ({r['identity']}, {r['denied_reason']}): \"{r['raw_transcript'][:60]}\"" for r in rows]


def check_sentinel(conn, state: dict) -> list:
    """Sentinel's own alert triggers: low disk, a service down (Ollama or
    the DB), or a burst of agent crashes. Uses the latest snapshot only --
    collect_health() must be called by something (--sentinel-check or a
    cron entry) for this to have fresh data; this doesn't collect itself."""
    snap = db.latest_health_snapshot(conn)
    if not snap:
        return []
    messages = []
    last_id = state.get("sentinel_last_snapshot_id", 0)
    if snap["id"] <= last_id:
        return []  # already alerted on this exact snapshot
    state["sentinel_last_snapshot_id"] = snap["id"]

    if snap["disk_percent"] is not None and snap["disk_percent"] > 90:
        messages.append(f"Low disk: {snap['disk_percent']}% used")
    if not snap["ollama_ok"]:
        messages.append("Ollama is not reachable -- local model calls will fail")
    if not snap["db_ok"]:
        messages.append("Database is not reachable")
    if not snap["internet_ok"]:
        messages.append("No internet connectivity detected")
    if snap["battery_percent"] is not None and snap["battery_percent"] < 15 and not snap["battery_plugged"]:
        messages.append(f"Battery low: {snap['battery_percent']}%, not plugged in")
    if snap["cpu_percent"] is not None and snap["cpu_percent"] > 90:
        messages.append(f"High CPU: {snap['cpu_percent']}%")
    if snap["ram_percent"] is not None and snap["ram_percent"] > 90:
        messages.append(f"High RAM: {snap['ram_percent']}%")
    if snap["cpu_temp_c"] is not None and snap["cpu_temp_c"] > 85:
        # Real check, not dead code: cpu_temp_c is None on this machine
        # (powermetrics needs sudo, confirmed unavailable) so this never
        # fires here -- it's live the moment it runs somewhere temp IS
        # readable, same "real attempt, not a stub" stance as sentinel.py.
        messages.append(f"High CPU temperature: {snap['cpu_temp_c']}°C")

    recent_tasks = db.recent_tasks(conn, limit=20)
    recent_failed = sum(1 for t in recent_tasks if t["status"] == "failed")
    if recent_failed >= 5:
        messages.append(f"{recent_failed} of the last 20 tasks failed -- possible agent crash pattern")

    return messages


def check_payment_failures(conn, state: dict) -> list:
    """Chrome Developer Bot / Offer A: a Razorpay Payment Link that
    expired or was cancelled, or any payment_transactions row (Stripe/
    Subscriptions/UPI) that failed."""
    links = conn.execute(
        "SELECT * FROM payment_links WHERE id > ? AND status IN ('cancelled', 'expired') ORDER BY id",
        (state.get("payment_failures_links_last_id", 0),),
    ).fetchall()
    links = [dict(r) for r in links]
    all_links = conn.execute("SELECT id FROM payment_links ORDER BY id DESC LIMIT 1").fetchone()
    if all_links:
        state["payment_failures_links_last_id"] = max(state.get("payment_failures_links_last_id", 0), all_links["id"])

    txns = conn.execute(
        "SELECT * FROM payment_transactions WHERE id > ? AND status = 'failed' ORDER BY id",
        (state.get("payment_failures_txn_last_id", 0),),
    ).fetchall()
    txns = [dict(r) for r in txns]
    all_txns = conn.execute("SELECT id FROM payment_transactions ORDER BY id DESC LIMIT 1").fetchone()
    if all_txns:
        state["payment_failures_txn_last_id"] = max(state.get("payment_failures_txn_last_id", 0), all_txns["id"])

    return (
        [f"Payment link #{r['id']} {r['status']}: ₹{r['amount_inr']} — {r['description'][:50]}" for r in links]
        + [f"{r['gateway']} payment failed: {r['currency']} {r['amount']} — {r['description'][:50]}" for r in txns]
    )


def check_website_errors(conn, state: dict) -> list:
    """Chrome Developer Bot: P0/P1 findings from a website review --
    console errors, missing security headers, exposed secrets."""
    rows = conn.execute(
        "SELECT * FROM website_review_findings WHERE id > ? AND severity IN ('P0', 'P1') ORDER BY id",
        (state.get("website_errors_last_id", 0),),
    ).fetchall()
    rows = [dict(r) for r in rows]
    if rows:
        state["website_errors_last_id"] = max(r["id"] for r in rows)
    return [f"Review #{r['review_id']} [{r['severity']}/{r['category']}]: {r['description'][:80]}" for r in rows]


def check_seo_issues(conn, state: dict) -> list:
    """Chrome Developer Bot: SEO-category findings from a website review."""
    rows = conn.execute(
        "SELECT * FROM website_review_findings WHERE id > ? AND category = 'seo' ORDER BY id",
        (state.get("seo_issues_last_id", 0),),
    ).fetchall()
    rows = [dict(r) for r in rows]
    if rows:
        state["seo_issues_last_id"] = max(r["id"] for r in rows)
    return [f"Review #{r['review_id']} SEO: {r['description'][:80]}" for r in rows]


def check_deployment_ready(conn, state: dict) -> list:
    """Chrome Developer Bot: a website review that completed and got the
    CEO deployment-ready green light."""
    rows = conn.execute(
        "SELECT * FROM website_reviews WHERE id > ? AND status = 'completed' AND deployment_ready = 1 ORDER BY id",
        (state.get("deployment_ready_last_id", 0),),
    ).fetchall()
    rows = [dict(r) for r in rows]
    all_reviews = conn.execute("SELECT id FROM website_reviews ORDER BY id DESC LIMIT 1").fetchone()
    if all_reviews:
        state["deployment_ready_last_id"] = max(state.get("deployment_ready_last_id", 0), all_reviews["id"])
    return [f"Deployment ready: {r['url']} (SEO {r['seo_score']}, UI {r['ui_score']})" for r in rows]


def check_ceo_failures(conn, state: dict) -> list:
    """CEO Health Monitor's alert path -- a genuinely new CEO task
    failure since last sweep. Rare after routing.py's fix (ceo is QA-
    exempt now); this fires for the remaining real case: a `critical`-
    risk CEO goal that needed cloud escalation and ANTHROPIC_API_KEY
    isn't set."""
    rows = conn.execute(
        "SELECT * FROM tasks WHERE agent_id = 'ceo' AND status = 'failed' AND id > ? ORDER BY id",
        (state.get("ceo_failures_last_id", 0),),
    ).fetchall()
    rows = [dict(r) for r in rows]
    all_ceo = conn.execute("SELECT id FROM tasks WHERE agent_id = 'ceo' ORDER BY id DESC LIMIT 1").fetchone()
    if all_ceo:
        state["ceo_failures_last_id"] = max(state.get("ceo_failures_last_id", 0), all_ceo["id"])
    return [f"CEO task #{r['id']} failed: {r['goal'][:70]} — {(r['result'] or '')[:80]}" for r in rows]


def check_worker_pool_failures(conn, state: dict) -> list:
    """Worker Pool: a queued task that failed during dispatch."""
    rows = conn.execute(
        "SELECT * FROM work_queue WHERE id > ? AND status = 'failed' ORDER BY id",
        (state.get("worker_failures_last_id", 0),),
    ).fetchall()
    rows = [dict(r) for r in rows]
    if rows:
        state["worker_failures_last_id"] = max(r["id"] for r in rows)
    return [f"Worker task #{r['id']} [{r['kind']}] failed: {(r['error'] or '')[:80]}" for r in rows]


def check_queue_overflow(conn, state: dict) -> list:
    """Worker Pool: queue depth over the hard ceiling right now -- a
    point-in-time check (not cursor-based like the others), since
    overflow is a current-state condition, not a discrete event."""
    from . import config
    depth = db.queue_depth(conn, status="queued")
    if depth > config.WORKER_QUEUE_MAX_SIZE:
        return [f"Queue overflow: {depth} tasks queued, over the {config.WORKER_QUEUE_MAX_SIZE} limit"]
    return []


def check_worker_critical_resource(conn, state: dict) -> list:
    """Worker Pool: system genuinely under load AND the queue is
    overflowing at the same time -- a compound signal specific to worker
    load, distinct from check_sentinel's generic high-CPU/RAM alert
    (which fires on either condition alone, regardless of the queue)."""
    from . import config, sentinel
    depth = db.queue_depth(conn, status="queued")
    if depth <= config.WORKER_QUEUE_MAX_SIZE:
        return []
    snap = db.latest_health_snapshot(conn)
    if not snap:
        return []
    if (snap["cpu_percent"] or 0) > 85 and (snap["ram_percent"] or 0) > 85:
        return [f"Critical resource usage under worker load: CPU {snap['cpu_percent']}% RAM {snap['ram_percent']}%, queue depth {depth}"]
    return []


def check_security_posture(conn, state: dict) -> list:
    """Watches security_posture_scan()'s (OPS-002) platform-wide runs --
    business_id IS NULL rows specifically, since review()'s per-business
    scans share this same table with a different meaning. Alerts once per
    new scan, and only when the score isn't a clean 100 -- something
    calling --security-scan on a schedule is what actually produces new
    rows here; this check just makes sure a drop doesn't sit silent in
    the DB until someone happens to open the dashboard."""
    row = conn.execute("SELECT * FROM security_reports WHERE business_id IS NULL ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return []
    row = dict(row)
    last_id = state.get("security_posture_last_id", 0)
    if row["id"] <= last_id:
        return []
    state["security_posture_last_id"] = row["id"]
    if row["score"] >= 100:
        return []
    findings = json.loads(row["findings"] or "[]")
    findings_line = "; ".join(f"{f.get('type')}: {f.get('check')}" for f in findings[:5]) or "no findings listed"
    return [f"Security posture score is {row['score']}/100 -- {findings_line}"]


CHECKS = {
    "revenue": check_revenue,
    "security": check_security,
    "security_posture": check_security_posture,
    "website_downtime": check_website_downtime,
    "agent_failures": check_agent_failures,
    "critical_ceo_decisions": check_critical_ceo_decisions,
    "critical_bugs": check_critical_bugs,
    "audit_critical_findings": check_audit_critical_findings,
    "fix_completed": check_fix_completed,
    "sentinel": check_sentinel,
    "voice_denied": check_voice_denied,
    "payment_failures": check_payment_failures,
    "website_errors": check_website_errors,
    "seo_issues": check_seo_issues,
    "deployment_ready": check_deployment_ready,
    "ceo_failures": check_ceo_failures,
    "worker_pool_failures": check_worker_pool_failures,
    "queue_overflow": check_queue_overflow,
    "worker_critical_resource": check_worker_critical_resource,
}


def run_security_posture_check(token: str, chat_id: str) -> dict:
    """Scoped, standalone version of the security_posture category --
    reads/writes the same .alerts_sync_state.json (only its own
    "security_posture_last_id" key), but doesn't touch or evaluate any of
    the other 17 CHECKS categories. Deliberately separate from
    run_sweep()/--alerts-sweep: that sweep has never been run on this
    machine, so its per-category state is unseeded and it would dump
    years of historical backlog (old bugs, old CEO decisions, old voice
    denials...) the first time it runs -- exactly what a 24/7 security-
    score cron job must not do. Wire this into cron instead."""
    state = _load_state()
    with db.get_conn() as conn:
        messages = check_security_posture(conn, state)
    _save_state(state)
    if messages:
        ts.alert(token, chat_id, "security_posture", "\n".join(f"- {m}" for m in messages))
    return {"security_posture": len(messages)}


def run_sentinel_alert_check(token: str, chat_id: str) -> dict:
    """Standalone version of the sentinel category, same reasoning as
    run_security_posture_check() above: reuses the existing check_sentinel
    threshold logic and the same .alerts_sync_state.json (only its own
    "sentinel_last_snapshot_id" key), but never touches the other 17
    CHECKS categories or their unseeded historical backlog. Pair with a
    cron entry that runs --sentinel-check first to produce a fresh
    snapshot -- this only reads the latest one, it doesn't collect."""
    state = _load_state()
    with db.get_conn() as conn:
        messages = check_sentinel(conn, state)
    _save_state(state)
    if messages:
        ts.alert(token, chat_id, "sentinel", "\n".join(f"- {m}" for m in messages))
    return {"sentinel": len(messages)}


def run_sweep(token: str, chat_id: str) -> dict:
    state = _load_state()
    sent = {}
    with db.get_conn() as conn:
        for category, check_fn in CHECKS.items():
            messages = check_fn(conn, state)
            sent[category] = len(messages)
            if messages:
                text = "\n".join(f"- {m}" for m in messages[:15])
                if len(messages) > 15:
                    text += f"\n...and {len(messages) - 15} more"
                ts.alert(token, chat_id, category, text)
    _save_state(state)
    return sent
