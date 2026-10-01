"""
JSON API for the Next.js dashboard. Loopback (127.0.0.1) traffic is
always trusted, no auth -- same trust model as the CLI. LAN/mobile access
(Task 13, Founder Command Center) is real but opt-in: set SHAKTHI_API_HOST
to a non-loopback address AND SHAKTHI_API_TOKEN to a real secret, and
every request that doesn't originate from loopback must present that
token (X-Shakthi-Token header or ?token= query param) or gets a 401. No
token configured -> the server refuses to bind anywhere but loopback,
it does not silently expose itself. See README "Security gaps" and the
Founder Command Center README section for mobile setup.

stdlib http.server, not FastAPI -- no new dependency for a handful of
read-mostly endpoints returning data the CLI commands already compute.
Reaching for a framework here would be the first dependency added purely
for the API layer; this doesn't need one yet.
"""
import json
import os
import platform
import socket
import threading
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import ceo as ceo_mod
from . import config, db, finance, initiatives, pa_angella, personal_plane, security, sentinel, voice, website_health
from .jobs import research_daily, publish_content

import psutil

ROUTES = {}

# Founder Command Center mobile/LAN access (Task 13). Real security
# boundary, not cosmetic: SHAKTHI_API_TOKEN, when set, is required on
# every request that does NOT originate from loopback (127.0.0.1/::1).
# Loopback traffic -- every existing dashboard server-component fetch,
# every test, every CLI call -- is exempt so none of that has to change.
# Only a request arriving over the LAN (a phone on the same WiFi hitting
# the machine's real IP) is gated. The token is never logged and never
# echoed back in any response.
API_TOKEN = os.environ.get("SHAKTHI_API_TOKEN", "").strip()
LOOPBACK_ADDRESSES = {"127.0.0.1", "::1"}


def _real_lan_ip() -> str | None:
    """Best-effort real LAN IP -- opens a UDP socket to a public address
    (no packet actually sent, UDP connect() just picks the outbound
    interface) so this reflects the actual network interface in use,
    not just the first hostname resolution, which can return a
    Docker-internal or loopback address on some machines."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    return None


def route(path):
    def deco(fn):
        ROUTES[path] = fn
        return fn
    return deco


def _qs_int(qs, key):
    val = qs.get(key, [None])[0]
    return int(val) if val is not None else None


def _actor(qs):
    return qs.get("actor_id", ["owner"])[0], qs.get("actor_role", ["Owner"])[0]


@route("/api/personal/goals")
def personal_goals(qs):
    actor_id, _ = _actor(qs)
    return {"goals": personal_plane.list_goals(actor_id)}


@route("/api/personal/tasks")
def personal_tasks(qs):
    actor_id, _ = _actor(qs)
    return {"tasks": personal_plane.list_tasks(actor_id, qs.get("status", [None])[0])}


@route("/api/personal/reminders/due")
def personal_due_reminders(qs):
    from datetime import datetime, timezone
    actor_id, _ = _actor(qs)
    through = qs.get("through", [datetime.now(timezone.utc).isoformat()])[0]
    return {"reminders": personal_plane.list_due_reminders(actor_id, through)}


@route("/api/overview")
def overview(qs):
    with db.get_conn() as conn:
        return {
            "businesses": db.list_businesses(conn),
            "active_tasks": db.active_task_count(conn),
            "recent_tasks": db.recent_tasks(conn, limit=15),
            "agent_count": len(db.list_agents(conn)),
            "cost_summary": db.cost_summary(conn),
        }


@route("/api/ai-usage")
def ai_usage(qs):
    """Real daily AI usage for the dashboard's usage panel -- built from
    actual cost_ledger rows, never a guessed/hard-coded number.

    Cloud (Claude, this system's own API-key usage -- NOT the founder's
    personal claude.ai/ChatGPT app subscriptions, which no API exposes to
    a third-party dashboard): real calls/tokens/cost today, checked
    against an optional founder-set daily budget.

    ChatGPT: Shakthi_OS has no OpenAI integration at all (model_gateway.py
    only talks to Ollama and Anthropic) -- reported as not-integrated
    rather than a fabricated zero that implies a real, checked absence of
    usage.

    Local (Ollama): real calls/tokens today, plus an ESTIMATED remaining
    capacity for the rest of today, computed from the actual observed
    average seconds-per-call in the last 24h x the configured assumed
    operating hours. Local has no real limit -- this is a labeled
    estimate, not a quota.
    """
    from datetime import datetime, timezone

    today_start = datetime.now(timezone.utc).strftime("%Y-%m-%d 00:00:00")

    with db.get_conn() as conn:
        today_summary = {row["provider"]: row for row in db.cost_summary(conn, since=today_start)}
        intervals = db.local_call_intervals_seconds(conn, since=today_start, provider="ollama")

    claude_today = today_summary.get("claude", {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0})
    ollama_today = today_summary.get("ollama", {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0})

    budget = config.CLOUD_DAILY_BUDGET_USD or None
    spent = claude_today.get("cost_usd") or 0.0
    cloud = {
        "provider": "claude",
        "configured": bool(config.ANTHROPIC_API_KEY),
        "calls_today": claude_today.get("calls") or 0,
        "tokens_in_today": claude_today.get("tokens_in") or 0,
        "tokens_out_today": claude_today.get("tokens_out") or 0,
        "cost_usd_today": round(spent, 4),
        "daily_budget_usd": budget,
        "budget_remaining_usd": round(budget - spent, 4) if budget else None,
        "note": None if config.ANTHROPIC_API_KEY else "ANTHROPIC_API_KEY not set -- cloud escalation is currently unavailable, real usage today is 0.",
    }

    chatgpt = {
        "integrated": False,
        "note": "Shakthi_OS has no OpenAI/ChatGPT integration -- nothing real to report, not a checked zero.",
    }

    avg_interval = round(sum(intervals) / len(intervals), 1) if intervals else None
    remaining_seconds_today = None
    estimated_remaining_calls = None
    if avg_interval and avg_interval > 0:
        remaining_seconds_today = max(config.LOCAL_OPERATING_HOURS_PER_DAY * 3600 - sum(intervals), 0)
        estimated_remaining_calls = int(remaining_seconds_today // avg_interval)

    local = {
        "provider": "ollama",
        "calls_today": ollama_today.get("calls") or 0,
        "tokens_in_today": ollama_today.get("tokens_in") or 0,
        "tokens_out_today": ollama_today.get("tokens_out") or 0,
        "limit": "unlimited (local hardware, no provider quota)",
        "avg_seconds_per_call_observed_today": avg_interval,
        "assumed_operating_hours_per_day": config.LOCAL_OPERATING_HOURS_PER_DAY,
        "estimated_remaining_calls_today": estimated_remaining_calls,
        "calculation_basis": (
            f"avg gap between {len(intervals) + 1} real calls today x remaining assumed hours"
            if avg_interval else "not enough calls today yet to estimate (need 2+)"
        ),
    }

    return {"date": today_start[:10], "cloud": cloud, "chatgpt": chatgpt, "local": local}


@route("/api/agents")
def agents(qs):
    with db.get_conn() as conn:
        rows = db.list_agents(conn)
    for r in rows:
        r["allowed_tools"] = json.loads(r["allowed_tools"] or "[]")
    return {"agents": rows}


@route("/api/agent-reality")
def agent_reality(qs):
    with db.get_conn() as conn:
        return db.agent_reality_summary(conn)


@route("/api/agent-health")
def agent_health(qs):
    # Real signal only -- task count/failure count/last-activity from the
    # actual tasks table, over the same recent window
    # report_generators.agent_health_report_text() already uses (limit
    # 200). No fabricated latency/escalation numbers -- this system has no
    # per-agent timing or escalation tracker yet, so this endpoint doesn't
    # claim to have one.
    with db.get_conn() as conn:
        agent_rows = db.list_agents(conn)
        tasks = db.recent_tasks(conn, limit=200)

    by_agent = {}
    for t in tasks:
        bucket = by_agent.setdefault(t["agent_id"], {"task_count": 0, "failed_count": 0, "last_activity": None})
        bucket["task_count"] += 1
        if t["status"] == "failed":
            bucket["failed_count"] += 1
        if bucket["last_activity"] is None or t["created_at"] > bucket["last_activity"]:
            bucket["last_activity"] = t["created_at"]

    result = []
    for a in agent_rows:
        stats = by_agent.get(a["id"], {"task_count": 0, "failed_count": 0, "last_activity": None})
        result.append({
            "id": a["id"], "name": a["name"], "layer": a["layer"],
            "local_model": a["local_model"], "default_model_tier": a["default_model_tier"],
            "task_count": stats["task_count"], "failed_count": stats["failed_count"],
            "last_activity": stats["last_activity"],
        })
    return {"agents": result, "window": "last 200 tasks system-wide"}


@route("/api/ceo/decisions")
def ceo_decisions(qs):
    with db.get_conn() as conn:
        return {"decisions": db.recent_decisions(conn, limit=_qs_int(qs, "limit") or 20)}


@route("/api/ceo/health")
def ceo_health(qs):
    from . import ceo_health_monitor
    with db.get_conn() as conn:
        return ceo_health_monitor.ceo_status(conn)


@route("/api/incidents")
def incidents_list(qs):
    from . import incident_manager
    status = qs.get("status", [None])[0]
    severity = qs.get("severity", [None])[0]
    with db.get_conn() as conn:
        rows = db.list_incidents(conn, status=status, severity=severity, limit=_qs_int(qs, "limit") or 100)
        mttr = incident_manager.mttr_seconds(conn)
    for r in rows:
        r["support_team"] = json.loads(r["support_team"] or "[]")
    open_statuses = ("NEW", "ACKNOWLEDGED", "INVESTIGATING", "FIXING", "VERIFYING", "READY_TO_DEPLOY")
    return {
        "incidents": rows, "mttr_seconds": mttr,
        "open_count": sum(1 for r in rows if r["status"] in open_statuses),
        "critical_count": sum(1 for r in rows if r["severity"] == "P0" and r["status"] in open_statuses),
    }


@route("/api/incidents/detail")
def incident_detail(qs):
    incident_number = qs.get("incident_number", [None])[0]
    if not incident_number:
        return {"error": "incident_number is required"}
    with db.get_conn() as conn:
        incident = db.get_incident(conn, incident_number=incident_number)
        if not incident:
            return {"error": f"no such incident: {incident_number}"}
        events = db.incident_events(conn, incident["id"])
    incident["support_team"] = json.loads(incident["support_team"] or "[]")
    return {"incident": incident, "events": events}


@route("/api/incidents/sweep")
def incidents_sweep(qs):
    from . import incident_scheduler
    urls = qs.get("website_urls", [None])[0]
    result = incident_scheduler.run_detection_sweep(website_urls=urls.split(",") if urls else None)
    return result


@route("/api/governor")
def governor_status_route(qs):
    from . import governor
    with db.get_conn() as conn:
        return governor.governor_status(conn)


@route("/api/finance/report")
def finance_report(qs):
    period = qs.get("period", ["monthly"])[0]
    business_id = _qs_int(qs, "business_id")
    return finance.generate_report(period, business_id=business_id)


@route("/api/finance/all-businesses")
def finance_all(qs):
    period = qs.get("period", ["monthly"])[0]
    with db.get_conn() as conn:
        businesses = db.list_businesses(conn)
    return {"period": period, "reports": [
        {"business": b, "report": finance.generate_report(period, business_id=b["id"])}
        for b in businesses
    ]}


@route("/api/security/latest")
def security_latest(qs):
    business_id = _qs_int(qs, "business_id")
    with db.get_conn() as conn:
        report = db.latest_security_report(conn, business_id=business_id)
        denied = db.recent_tool_calls(conn, limit=10, decision="denied")
    if report:
        report["findings"] = json.loads(report["findings"])
    return {"latest_report": report, "recent_denied_calls": denied}


@route("/api/security/scan")
def security_scan(qs):
    business_id = _qs_int(qs, "business_id")
    return security.review(business_id=business_id)


@route("/api/client-success/overview")
def client_success_overview(qs):
    from . import customer_success
    with db.get_conn() as conn:
        clients = db.list_leads(conn, status="won", limit=1000)
        for c in clients:
            health = db.latest_client_health_score(conn, c["id"])
            if health:
                health["signals"] = json.loads(health["signals"])
            c["health"] = health
    scores = [c["health"]["score"] for c in clients if c["health"]]
    avg_score = round(sum(scores) / len(scores)) if scores else None
    at_risk_count = sum(1 for s in scores if s < customer_success.AT_RISK_THRESHOLD)
    return {"clients": clients, "total_clients": len(clients), "avg_health_score": avg_score, "at_risk_count": at_risk_count}


@route("/api/client-success/at-risk")
def client_success_at_risk(qs):
    from . import customer_success
    with db.get_conn() as conn:
        clients = db.list_leads(conn, status="won", limit=1000)
        at_risk = []
        for c in clients:
            health = db.latest_client_health_score(conn, c["id"])
            if health and health["score"] < customer_success.AT_RISK_THRESHOLD:
                health["signals"] = json.loads(health["signals"])
                c["health"] = health
                at_risk.append(c)
    return {"at_risk_clients": at_risk}


@route("/api/costs")
def costs(qs):
    with db.get_conn() as conn:
        return {"cost_summary": db.cost_summary(conn), "recent_tool_calls": db.recent_tool_calls(conn, limit=30)}


@route("/api/websites")
def websites(qs):
    from pathlib import Path
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM sites ORDER BY business_id, id").fetchall()
        rows = [dict(r) for r in rows]
        businesses = {b["id"]: b["name"] for b in db.list_businesses(conn)}
    for r in rows:
        r["business_name"] = businesses.get(r["business_id"], "?")
        r["file_exists"] = bool(r["local_path"] and Path(r["local_path"]).exists())
    return {"sites": rows}


@route("/api/bugs")
def bugs(qs):
    status = qs.get("status", [None])[0]
    severity = qs.get("severity", [None])[0]
    with db.get_conn() as conn:
        rows = db.list_bugs(conn, status=status, severity=severity, limit=100)
    return {"bugs": rows}


@route("/api/bugs/detail")
def bug_detail(qs):
    bug_id = _qs_int(qs, "id")
    if bug_id is None:
        return {"error": "id is required"}
    with db.get_conn() as conn:
        bug = db.get_bug(conn, bug_id)
        if not bug:
            return {"error": f"no such bug: {bug_id}"}
        events = db.bug_events(conn, bug_id)
        patches = db.list_patches(conn, bug_id=bug_id)
    return {"bug": bug, "events": events, "patches": patches}


@route("/api/patches")
def patches(qs):
    bug_id = _qs_int(qs, "bug_id")
    with db.get_conn() as conn:
        rows = db.list_patches(conn, bug_id=bug_id, limit=100)
    return {"patches": rows}


@route("/api/audits")
def audits(qs):
    with db.get_conn() as conn:
        rows = db.list_audits(conn, limit=20)
    return {"audits": rows}


@route("/api/audits/detail")
def audit_detail(qs):
    audit_id = _qs_int(qs, "id")
    if audit_id is None:
        return {"error": "id is required"}
    with db.get_conn() as conn:
        audit_row = db.get_audit(conn, audit_id)
        if not audit_row:
            return {"error": f"no such audit: {audit_id}"}
        findings = db.audit_findings(conn, audit_id)
    return {"audit": audit_row, "findings": findings}


@route("/api/sentinel/latest")
def sentinel_latest(qs):
    with db.get_conn() as conn:
        snap = db.latest_health_snapshot(conn)
    return {"snapshot": snap, "services": sentinel.service_status()}


@route("/api/sentinel/collect")
def sentinel_collect(qs):
    snap = sentinel.collect_health()
    return {"snapshot": snap, "services": sentinel.service_status()}


@route("/api/sentinel/history")
def sentinel_history(qs):
    with db.get_conn() as conn:
        return {"snapshots": db.recent_health_snapshots(conn, limit=_qs_int(qs, "limit") or 50)}


@route("/api/website-health/latest")
def website_health_latest(qs):
    with db.get_conn() as conn:
        sites = db.list_watched_websites(conn)
        rows = []
        for site in sites:
            latest = db.latest_health_check(conn, site["id"])
            rows.append({**site, "latest_check": latest, "in_alert": website_health.alert_flag(site, latest)})
    return {"sites": rows}


@route("/api/website-health/refresh")
def website_health_refresh(qs):
    # Real synchronous check-and-record, same "GET route with a real write
    # side effect" pattern as /api/sentinel/collect -- this framework is
    # GET-only (see the module docstring), so manual refresh is a GET that
    # does real work, not a fetch of stale data.
    results = website_health.check_all_watched_sites()
    return {"sites": results}


@route("/api/website-health/incidents")
def website_health_incidents(qs):
    with db.get_conn() as conn:
        incidents = db.list_incidents(conn, limit=_qs_int(qs, "limit") or 50)
        sites_by_id = {s["id"]: s for s in db.list_watched_websites(conn, active_only=False)}
    for inc in incidents:
        site = sites_by_id.get(inc["website_id"])
        inc["website_label"] = site["label"] if site else f"website #{inc['website_id']}"
        inc["website_url"] = site["url"] if site else None
    return {"incidents": incidents}


@route("/api/website-health/history")
def website_health_history(qs):
    website_id = _qs_int(qs, "website_id")
    if website_id is None:
        return {"error": "website_id is required"}
    with db.get_conn() as conn:
        return {"checks": db.history_health_checks(conn, website_id, limit=_qs_int(qs, "limit") or 50)}


@route("/api/knowledge")
def knowledge_list(qs):
    category = qs.get("category", [None])[0]
    with db.get_conn() as conn:
        return {"documents": db.list_knowledge(conn, category=category, limit=100)}


@route("/api/voice/recent")
def voice_recent(qs):
    with db.get_conn() as conn:
        return {"commands": db.recent_voice_commands(conn, limit=_qs_int(qs, "limit") or 20)}


@route("/api/voice/execute")
def voice_execute(qs):
    """Execute browser-transcribed speech through the existing governed loop.

    Browser speech synthesis handles the reply, so the server does not also
    play it through the PC speaker. With no owner passphrase in a URL, this
    deliberately runs as Guest and retains the existing permission boundary.
    """
    text = (qs.get("text", [""])[0] or "").strip()
    language = (qs.get("language", ["en"])[0] or "en").split("-")[0].lower()
    if not text:
        return {"error": "empty transcript"}
    if language not in {"en", "hi", "gu"}:
        language = "en"
    return voice._transcribe_and_execute(
        audio=None,
        identity_passphrase=None,
        speak_response=False,
        transcription={"text": text, "language": language, "confidence": 1.0},
    )


@route("/api/tasks")
def tasks(qs):
    status = qs.get("status", [None])[0]
    with db.get_conn() as conn:
        return {"tasks": db.list_tasks_full(conn, status=status, limit=100), "counts": db.task_status_counts(conn)}


@route("/api/memory")
def memory(qs):
    layer = qs.get("layer", [None])[0]
    with db.get_conn() as conn:
        return {"entries": db.list_all_memory(conn, layer=layer, limit=100)}


@route("/api/trading/strategies")
def trading_strategies(qs):
    status = qs.get("status", [None])[0]
    with db.get_conn() as conn:
        return {"strategies": db.list_strategies(conn, status=status)}


@route("/api/trading/positions")
def trading_positions(qs):
    status = qs.get("status", [None])[0]
    with db.get_conn() as conn:
        return {"positions": db.list_positions(conn, status=status)}


@route("/api/trading/journal")
def trading_journal(qs):
    limit = _qs_int(qs, "limit") or 100
    with db.get_conn() as conn:
        return {"journal": db.list_journal(conn, limit=limit)}


@route("/api/trading/price")
def trading_price(qs):
    symbol = qs.get("symbol", [None])[0]
    if not symbol:
        return {"error": "symbol is required"}
    from . import market_data
    try:
        return {"symbol": symbol, "price": market_data.current_price(symbol)}
    except market_data.MarketDataError as e:
        return {"error": str(e)}


@route("/api/peopledesk/staff")
def peopledesk_staff(qs):
    owner_email = qs.get("owner_email", [None])[0]
    status = qs.get("status", ["active"])[0]
    if not owner_email:
        return {"error": "owner_email is required"}
    with db.get_conn() as conn:
        return {"staff": db.list_staff(conn, owner_email, status=status)}


@route("/api/peopledesk/payroll")
def peopledesk_payroll(qs):
    owner_email = qs.get("owner_email", [None])[0]
    date_from = qs.get("date_from", [None])[0]
    date_to = qs.get("date_to", [None])[0]
    if not (owner_email and date_from and date_to):
        return {"error": "owner_email, date_from, date_to are required"}
    from . import peopledesk
    return {"summary": peopledesk.payroll_summary(owner_email, date_from, date_to)}


@route("/api/failure-analyses")
def failure_analyses_list(qs):
    status = qs.get("status", [None])[0]
    with db.get_conn() as conn:
        return {"analyses": db.list_failure_analyses(conn, status=status)}


@route("/api/pa-angella/status")
def pa_angella_status(qs):
    with db.get_conn() as conn:
        last_task = db.last_task_for_agent(conn, "pa_angella")
        recent_count = db.recent_task_count_for_agent(conn, "pa_angella", minutes=30)
    return {"last_task": last_task, "active": recent_count > 0, "recent_task_count": recent_count}


# Founder Command Center -- a real GET-triggered mutation (PA Angella ->
# CEO dispatch), not REST-pure, but this framework is already explicitly
# "trusted-local-operator, no auth" (see module docstring) and adding a
# whole do_POST code path for one endpoint isn't worth it yet.
@route("/api/command-center/submit")
def command_center_submit(qs):
    text = (qs.get("text", [""])[0] or "").strip()
    if not text:
        return {"error": "empty command"}
    return pa_angella.refine_and_send_to_ceo(text)


@route("/api/command-center/logs")
def command_center_logs(qs):
    with db.get_conn() as conn:
        return {"events": db.recent_task_events(conn, limit=_qs_int(qs, "limit") or 50)}


@route("/api/jarvis/route")
def jarvis_route(qs):
    """Return a deterministic, explainable specialist preview before dispatch."""
    goal = (qs.get("text", [""])[0] or "").strip()
    if not goal:
        return {"error": "empty mission"}
    from .routing import classify_risk
    lowered = goal.lower()
    keyword_groups = {
        "security": ("security", "vulnerability", "credential", "secret"),
        "website": ("site", "website", "launch", "domain", "dashboard"),
        "marketing": ("market", "campaign", "content", "customer", "sales"),
        "finance": ("finance", "payment", "revenue", "budget", "invoice"),
        "qa": ("check", "verify", "test", "audit", "review"),
    }
    with db.get_conn() as conn:
        agents = db.list_agents(conn)
    chosen = None
    for group, keywords in keyword_groups.items():
        if any(keyword in lowered for keyword in keywords):
            chosen = next((agent for agent in agents if group in agent["id"].lower() or group in agent["name"].lower()), None)
            if chosen:
                break
    chosen = chosen or next((agent for agent in agents if agent["id"] == "ceo"), None) or (agents[0] if agents else None)
    if not chosen:
        return {"error": "no registered agents"}
    risk = classify_risk(goal)
    from .jarvis_mediator import build_professional_task
    agent_view = {"id": chosen["id"], "name": chosen["name"], "layer": chosen["layer"], "allowed_tools": json.loads(chosen["allowed_tools"] or "[]")}
    return {"risk": risk, "agent": agent_view, "professional_task": build_professional_task(goal, agent_view, risk)}


@route("/api/initiatives")
def initiatives_list(qs):
    status = qs.get("status", [None])[0]
    with db.get_conn() as conn:
        return {"initiatives": db.list_initiatives(conn, status=status)}


# Smart Copy (Shakthi_OS 3.1.1) -- same GET-triggered-mutation convention as
# /api/command-center/submit above: this framework is trusted-local-operator,
# no auth, so a real do_POST path isn't worth adding for one endpoint yet.
@route("/api/initiatives/smart-copy")
def initiatives_smart_copy(qs):
    source_id = _qs_int(qs, "id")
    if not source_id:
        return {"error": "missing id"}
    title = (qs.get("title", [""])[0] or "").strip() or None
    note = (qs.get("note", [""])[0] or "").strip() or None
    try:
        new_initiative = initiatives.clone(source_id, new_title=title, note=note)
    except ValueError as e:
        return {"error": str(e)}
    return {"initiative": new_initiative}


@route("/api/dhansetu/courses")
def dhansetu_courses(qs):
    status = qs.get("status", [None])[0]
    with db.get_conn() as conn:
        return {"courses": db.list_courses(conn, status=status, limit=100)}


@route("/api/dhansetu/content-queue")
def dhansetu_content_queue(qs):
    with db.get_conn() as conn:
        items = db.list_content_queue(conn, limit=100)
    return {"items": [i for i in items if i.get("platform")]}  # Dhansetu-tagged rows only, marketing.py's own rows never set platform


@route("/api/dhansetu/links")
def dhansetu_links(qs):
    with db.get_conn() as conn:
        return {"links": db.list_links(conn, active_only=False)}


@route("/api/website-projects")
def website_projects(qs):
    status = qs.get("status", [None])[0]
    with db.get_conn() as conn:
        projects = db.list_website_projects(conn, status=status, limit=50)
        businesses = {b["id"]: b["name"] for b in db.list_businesses(conn)}
    for p in projects:
        p["business_name"] = businesses.get(p["business_id"], "?")
    from . import template_registry
    return {"projects": projects, "templates": sorted(template_registry.TEMPLATES)}


@route("/api/corrections")
def corrections(qs):
    with db.get_conn() as conn:
        rows = db.list_corrections(conn, limit=_qs_int(qs, "limit") or 20)
    return {"corrections": rows}


@route("/api/corrections/detail")
def correction_detail(qs):
    correction_id = _qs_int(qs, "id")
    if correction_id is None:
        return {"error": "id is required"}
    with db.get_conn() as conn:
        row = db.get_correction(conn, correction_id)
        if not row:
            return {"error": f"no such correction: {correction_id}"}
        findings = db.correction_findings(conn, correction_id)
    return {"correction": row, "findings": findings}


@route("/api/payments")
def payments_list(qs):
    status = qs.get("status", [None])[0]
    with db.get_conn() as conn:
        rows = db.list_payment_links(conn, status=status, limit=_qs_int(qs, "limit") or 50)
    total_paid = sum(r["amount_inr"] for r in rows if r["status"] == "paid")
    return {"payment_links": rows, "total_paid_inr": total_paid}


@route("/api/website-reviews")
def website_reviews(qs):
    with db.get_conn() as conn:
        rows = db.list_website_reviews(conn, limit=_qs_int(qs, "limit") or 20)
    return {"reviews": rows}


@route("/api/website-reviews/detail")
def website_review_detail(qs):
    review_id = _qs_int(qs, "id")
    if review_id is None:
        return {"error": "id is required"}
    with db.get_conn() as conn:
        review = db.get_website_review(conn, review_id)
        if not review:
            return {"error": f"no such review: {review_id}"}
        findings = db.website_review_findings(conn, review_id)
    return {"review": review, "findings": findings}


@route("/api/gateway-activity")
def gateway_activity(qs):
    """No live credential check here -- payments.py/payment_gateway_manager.py
    deliberately never store Razorpay/Stripe/UPI credentials, so the
    dashboard can't validate them without the founder re-entering secrets
    into a browser, which this project's payments design explicitly avoids.
    This reports real HISTORY instead: what's actually been used and paid."""
    with db.get_conn() as conn:
        links = db.list_payment_links(conn, limit=200)
        txns = db.list_payment_transactions(conn, limit=200)
    gateways = {}
    for r in links:
        g = gateways.setdefault("razorpay_link", {"count": 0, "paid_count": 0, "last_used": None})
        g["count"] += 1
        g["paid_count"] += 1 if r["status"] == "paid" else 0
        g["last_used"] = max(filter(None, [g["last_used"], r["created_at"]]))
    for r in txns:
        g = gateways.setdefault(r["gateway"], {"count": 0, "paid_count": 0, "last_used": None})
        g["count"] += 1
        g["paid_count"] += 1 if r["status"] == "paid" else 0
        g["last_used"] = max(filter(None, [g["last_used"], r["created_at"]]))
    return {"gateways": gateways}


@route("/api/workers")
def workers_list(qs):
    from . import load_manager, worker_pool
    worker_pool.ensure_workers_registered()
    with db.get_conn() as conn:
        workers = db.list_workers(conn)
        lb = load_manager.load_balancer_status(conn)
        queue = db.list_work_queue(conn, limit=_qs_int(qs, "limit") or 50)
    return {"workers": workers, "load_balancer": lb, "queue": queue}


@route("/api/health")
def health(qs):
    db_ok = Path(config.DB_PATH).exists()
    return {
        "db_ok": db_ok,
        "ollama_host": config.OLLAMA_HOST,
        "allow_exec": config.ALLOW_EXEC,
        "dry_run": config.TOOLS_DRY_RUN,
        "workspaces_dir": str(config.WORKSPACES_DIR),
        "hostname": socket.gethostname(),
    }


@route("/api/mac/runtime")
def mac_runtime(qs):
    """Current, read-only Mac host facts for the executive dashboard.

    Values are sampled on request and are never inferred from stale data or
    a decorative animation. GPU state remains explicit when no GPU utility
    can be found.
    """
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.home()))
    battery = psutil.sensors_battery()
    cpu_name = platform.processor() or platform.machine()

    gpu = {"state": "UNAVAILABLE", "name": None, "reason": "no GPU utility found on this Mac"}

    return {
        "source": "LIVE_LOCAL_SAMPLE",
        "sampled_at": time.time(),
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "cpu_name": cpu_name,
        "logical_cpus": psutil.cpu_count(),
        "cpu_percent": round(psutil.cpu_percent(interval=0.15), 1),
        "ram_percent": round(vm.percent, 1),
        "ram_total_bytes": vm.total,
        "disk_percent": round(disk.percent, 1),
        "disk_free_bytes": disk.free,
        "battery_percent": round(battery.percent, 1) if battery else None,
        "battery_plugged": bool(battery.power_plugged) if battery else None,
        "uptime_seconds": round(time.time() - psutil.boot_time()),
        "gpu": gpu,
        "api_port": int(os.environ.get("SHAKTHI_API_PORT", "8787")),
    }


# Real Linux compute node (gvc-ops-ai, 192.168.31.27), 2026-09-13 -- the
# founder's own machine, connected over the local network via a real,
# already-working SSH keypair (~/.ssh/shakthi_bridge_ed25519). Same
# discipline as mac_runtime() above: every field is a live sample taken
# THIS request, over a real SSH round-trip -- if the machine is
# unreachable, `reachable` is false and every other field is null, never a
# fabricated number. No new service runs on Linux for this; the Mac stays
# the one place querying/deciding, matching the founder's explicit
# "authority stays on Mac" architecture.
_LINUX_NODE_HOST = "blackboxops@192.168.31.27"
_LINUX_NODE_KEY = str(Path.home() / ".ssh" / "shakthi_bridge_ed25519")
_LINUX_REMOTE_SCRIPT = """
import json, os, socket, platform, time, subprocess
import psutil
vm = psutil.virtual_memory()
disk = psutil.disk_usage('/')

# Real external backup SSD (/dev/sda1), 2026-09-13 -- reported honestly:
# real usage if actually mounted at /mnt/backup_ssd, otherwise just its
# real raw capacity (from the kernel's own block-device size file) with
# mounted=false. Never a fabricated used/free split for an unmounted disk.
ext_storage = {"present": False}
try:
    with open("/sys/class/block/sda/size") as f:
        sectors = int(f.read().strip())
    ext_storage = {"present": True, "mounted": False, "total_bytes": sectors * 512, "used_bytes": None, "free_bytes": None, "percent": None}
    if os.path.ismount("/mnt/backup_ssd"):
        ext = psutil.disk_usage("/mnt/backup_ssd")
        ext_storage.update({"mounted": True, "total_bytes": ext.total, "used_bytes": ext.used, "free_bytes": ext.free, "percent": round(ext.percent, 1)})
except FileNotFoundError:
    pass

gpu = {"state": "UNAVAILABLE", "name": None, "reason": "no nvidia-smi found"}
try:
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=4,
    )
    if out.returncode == 0 and out.stdout.strip():
        name, util, mem_used, mem_total, temp = [p.strip() for p in out.stdout.strip().split(",")]
        gpu = {
            "state": "CONNECTED", "name": name,
            "utilization_percent": float(util), "mem_used_mb": float(mem_used),
            "mem_total_mb": float(mem_total), "temperature_c": float(temp),
        }
except FileNotFoundError:
    pass
except Exception as e:
    gpu = {"state": "DRIVER_ERROR", "name": None, "reason": str(e)}
print(json.dumps({
    "hostname": socket.gethostname(), "os": platform.system(), "kernel": platform.release(),
    "architecture": platform.machine(), "logical_cpus": psutil.cpu_count(),
    "cpu_percent": round(psutil.cpu_percent(interval=0.3), 1),
    "ram_percent": round(vm.percent, 1), "ram_total_bytes": vm.total,
    "disk_percent": round(disk.percent, 1), "disk_free_bytes": disk.free, "disk_total_bytes": disk.total,
    "ext_storage": ext_storage,
    "uptime_seconds": round(time.time() - psutil.boot_time()), "gpu": gpu,
}))
"""


@route("/api/linux/runtime")
def linux_runtime(qs):
    """Real Linux compute-node status, sampled live over SSH every request.

    See the module-level comment above _LINUX_NODE_HOST -- reachable=false
    with every stat null is the honest answer when the SSH round-trip
    fails, never a cached or invented last-known value.
    """
    import subprocess

    try:
        # Real bug found+fixed 2026-09-13: passing the script as a `-c`
        # argument let SSH's remote shell try to parse its newlines/quotes
        # before python3 ever saw it (concrete failure: "bash: line 2:
        # import: command not found"). Piping it over stdin to `python3 -`
        # instead sidesteps shell quoting entirely -- no string embedding,
        # no escaping to get wrong.
        result = subprocess.run(
            ["ssh", "-i", _LINUX_NODE_KEY, "-o", "BatchMode=yes", "-o", "ConnectTimeout=4",
             "-o", "StrictHostKeyChecking=accept-new", _LINUX_NODE_HOST, "python3", "-"],
            input=_LINUX_REMOTE_SCRIPT, capture_output=True, text=True, timeout=8,
        )
        if result.returncode != 0:
            return {"reachable": False, "sampled_at": time.time(), "error": (result.stderr or "SSH failed").strip()[:300]}
        stats = json.loads(result.stdout.strip())
        stats["reachable"] = True
        stats["sampled_at"] = time.time()
        return stats
    except subprocess.TimeoutExpired:
        return {"reachable": False, "sampled_at": time.time(), "error": "SSH timed out (Linux node unreachable)"}
    except Exception as e:
        return {"reachable": False, "sampled_at": time.time(), "error": str(e)[:300]}


@route("/api/v31/missions")
def v31_missions(qs):
    from shakthi.missions import MissionStore
    return {"missions": MissionStore().list()}


@route("/api/v31/world-model")
def v31_world_model(qs):
    from shakthi.world_model import WorldModel
    return {"entities": WorldModel().entities()}


@route("/api/v31/audit")
def v31_audit(qs):
    from shakthi.audit import AuditLog
    log = AuditLog()
    return {"chain_valid": log.verify(), "entries": log.entries()[:100]}


@route("/api/v31/events")
def v31_events(qs):
    from shakthi.event_bus import EventBus
    return {"events": EventBus().recent(limit=_qs_int(qs, "limit") or 100)}


@route("/api/v31/governance")
def v31_governance(qs):
    from shakthi.governance import AutonomyLevel, TruthState
    return {
        "autonomy_levels": [{"name": level.name, "value": int(level)} for level in AutonomyLevel],
        "truth_states": [state.value for state in TruthState],
    }


# Research Automation & Content Publishing Pipeline (Tasks #8+10)

@route("/api/research/fetch")
def research_fetch(qs):
    """Manual trigger for daily research job."""
    business_id = _qs_int(qs, "business_id") or 1
    generator = research_daily.InsightGenerator()
    result = generator.run(business_id)
    return result


@route("/api/research/preview")
def research_preview(qs):
    """Preview content conversion without publishing."""
    business_id = _qs_int(qs, "business_id") or 1
    publisher = publish_content.ContentPublisher()
    result = publisher.run(business_id, dry_run=True)
    return result


@route("/api/research/insights")
def research_insights(qs):
    """List recent research insights."""
    limit = _qs_int(qs, "limit") or 10
    status = qs.get("status", [None])[0]

    with db.get_conn() as conn:
        query = "SELECT * FROM research_insights ORDER BY created_at DESC LIMIT ?"
        params = [limit]

        if status:
            query = "SELECT * FROM research_insights WHERE status = ? ORDER BY created_at DESC LIMIT ?"
            params = [status, limit]

        insights = conn.execute(query, params).fetchall()
        return {
            "insights": [dict(i) for i in insights],
            "total": len(insights)
        }


@route("/api/research/publish")
def research_publish(qs):
    """Publish queued content to platforms."""
    business_id = _qs_int(qs, "business_id") or 1
    publisher = publish_content.ContentPublisher()
    result = publisher.run(business_id, dry_run=False)
    return result


@route("/api/research/job-log")
def research_job_log(qs):
    """Get research job execution history."""
    limit = _qs_int(qs, "limit") or 30

    with db.get_conn() as conn:
        logs = conn.execute(
            "SELECT * FROM research_job_log ORDER BY run_date DESC LIMIT ?",
            [limit]
        ).fetchall()
        return {
            "job_logs": [dict(l) for l in logs],
            "total": len(logs)
        }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep stdout clean; errors still surface via 500s below

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if API_TOKEN and self.client_address[0] not in LOOPBACK_ADDRESSES:
            supplied = self.headers.get("X-Shakthi-Token") or qs.get("token", [""])[0]
            if supplied != API_TOKEN:
                self._send(401, {"error": "missing or invalid token"})
                return
        handler = ROUTES.get(parsed.path)
        if not handler:
            self._send(404, {"error": f"no such route: {parsed.path}"})
            return
        try:
            result = handler(qs)
            self._send(200, result)
        except Exception as e:
            # Real bug found live (Task 13 verification, 2026-09-03):
            # under the heavy concurrent DB writes many simultaneous
            # forks produced tonight, the ORIGINAL exception was a real
            # "database is locked" from db.insert_task() -- and this
            # fallback error-logging call hit the SAME lock and raised
            # a second, uncaught exception, which crashed this whole
            # request thread before any response was ever sent (curl
            # saw "empty reply from server", not a clean 500). Logging
            # the error must never be able to prevent the client from
            # getting a real response, regardless of why the original
            # call failed.
            import traceback as tb_mod
            try:
                with db.get_conn() as conn:
                    db.log_error(conn, "api", parsed.path, str(e), tb_mod.format_exc())
            except Exception:
                pass
            self._send(500, {"error": str(e)})

    def do_POST(self):
        parsed = urlparse(self.path)
        if API_TOKEN and self.client_address[0] not in LOOPBACK_ADDRESSES:
            supplied = self.headers.get("X-Shakthi-Token", "")
            if supplied != API_TOKEN:
                self._send(401, {"error": "missing or invalid token"})
                return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            actor_id = body.get("actor_id", "owner")
            actor_role = body.get("actor_role", "Owner")
            request_id = body.get("request_id")
            if parsed.path == "/api/personal/goals":
                result = personal_plane.create_goal(body.get("title", ""), actor_id, actor_role, request_id)
            elif parsed.path == "/api/personal/tasks":
                result = personal_plane.create_task(body.get("title", ""), body.get("goal_id"), actor_id, actor_role, request_id)
            elif parsed.path == "/api/personal/reminders":
                result = personal_plane.create_reminder(body.get("title", ""), body.get("due_at", ""), actor_id, actor_role, request_id)
            else:
                self._send(404, {"error": f"no such route: {parsed.path}"})
                return
            self._send(201, result)
        except (ValueError, PermissionError, json.JSONDecodeError) as exc:
            self._send(400 if not isinstance(exc, PermissionError) else 403, {"error": str(exc)})
        except Exception as exc:
            self._send(500, {"error": str(exc)})

    def _send(self, status, payload):
        body = json.dumps(payload, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")  # localhost dev only
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


WEBSITE_HEALTH_CHECK_INTERVAL_SECONDS = 300  # 5 minutes -- real scheduled local checks


def _website_health_scheduler_loop():
    while True:
        try:
            website_health.check_all_watched_sites()
        except Exception as e:
            # A scheduler-thread crash must never take the whole API down --
            # log it via the same error table every other real failure uses.
            with db.get_conn() as conn:
                db.log_error(conn, "website_health_scheduler", "background_check", str(e), "")
        time.sleep(WEBSITE_HEALTH_CHECK_INTERVAL_SECONDS)


def serve(port: int = None, host: str = None):
    # Env-configurable host/port for LAN/mobile access (Task 13) --
    # SHAKTHI_API_HOST defaults to loopback-only, same as always. Binding
    # to a real LAN-reachable host without a token configured would make
    # the whole system (25 real agents, real financial/task data) reachable
    # by anyone on the WiFi with zero auth -- refuse and fall back to
    # loopback rather than silently doing that.
    port = port or int(os.environ.get("SHAKTHI_API_PORT", "8787"))
    host = host or os.environ.get("SHAKTHI_API_HOST", "127.0.0.1")
    if host not in ("127.0.0.1", "localhost") and not API_TOKEN:
        print(f"REFUSING to bind {host} without SHAKTHI_API_TOKEN set -- falling back to 127.0.0.1.")
        print("Set SHAKTHI_API_TOKEN to a real secret to enable LAN/mobile access.")
        host = "127.0.0.1"

    server = ThreadingHTTPServer((host, port), Handler)
    scheduler = threading.Thread(target=_website_health_scheduler_loop, daemon=True)
    scheduler.start()
    print(f"Shakthi API listening on http://{host}:{port}  (routes: {', '.join(sorted(ROUTES))})")
    if host not in ("127.0.0.1", "localhost"):
        lan_ip = _real_lan_ip()
        if lan_ip:
            print(f"LAN/mobile URL: http://{lan_ip}:{port}  (token required for non-loopback requests)")
        else:
            print("Bound to a non-loopback host but could not determine a real LAN IP -- check your network interface.")
    print(f"Website Health Watcher: background checks every {WEBSITE_HEALTH_CHECK_INTERVAL_SECONDS}s")
    server.serve_forever()


if __name__ == "__main__":
    serve()
