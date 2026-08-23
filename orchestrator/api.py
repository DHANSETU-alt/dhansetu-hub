"""
JSON API for the Next.js dashboard. Local-only, no auth -- same trust model
as the CLI (trusted-local-operator), explicitly not yet safe to expose
beyond localhost. See README "Security gaps."

stdlib http.server, not FastAPI -- no new dependency for a handful of
read-mostly endpoints returning data the CLI commands already compute.
Reaching for a framework here would be the first dependency added purely
for the API layer; this doesn't need one yet.
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import ceo as ceo_mod
from . import config, db, finance, security, sentinel

ROUTES = {}


def route(path):
    def deco(fn):
        ROUTES[path] = fn
        return fn
    return deco


def _qs_int(qs, key):
    val = qs.get(key, [None])[0]
    return int(val) if val is not None else None


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


@route("/api/agents")
def agents(qs):
    with db.get_conn() as conn:
        rows = db.list_agents(conn)
    for r in rows:
        r["allowed_tools"] = json.loads(r["allowed_tools"] or "[]")
    return {"agents": rows}


@route("/api/ceo/decisions")
def ceo_decisions(qs):
    with db.get_conn() as conn:
        return {"decisions": db.recent_decisions(conn, limit=_qs_int(qs, "limit") or 20)}


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


@route("/api/knowledge")
def knowledge_list(qs):
    category = qs.get("category", [None])[0]
    with db.get_conn() as conn:
        return {"documents": db.list_knowledge(conn, category=category, limit=100)}


@route("/api/voice/recent")
def voice_recent(qs):
    with db.get_conn() as conn:
        return {"commands": db.recent_voice_commands(conn, limit=_qs_int(qs, "limit") or 20)}


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


@route("/api/health")
def health(qs):
    import os
    from pathlib import Path
    db_ok = Path(config.DB_PATH).exists()
    return {
        "db_ok": db_ok,
        "ollama_host": config.OLLAMA_HOST,
        "allow_exec": config.ALLOW_EXEC,
        "dry_run": config.TOOLS_DRY_RUN,
        "workspaces_dir": str(config.WORKSPACES_DIR),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep stdout clean; errors still surface via 500s below

    def do_GET(self):
        parsed = urlparse(self.path)
        handler = ROUTES.get(parsed.path)
        if not handler:
            self._send(404, {"error": f"no such route: {parsed.path}"})
            return
        try:
            result = handler(parse_qs(parsed.query))
            self._send(200, result)
        except Exception as e:
            import traceback as tb_mod
            with db.get_conn() as conn:
                db.log_error(conn, "api", parsed.path, str(e), tb_mod.format_exc())
            self._send(500, {"error": str(e)})

    def _send(self, status, payload):
        body = json.dumps(payload, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")  # localhost dev only
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(port: int = 8787):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Shakthi API listening on http://127.0.0.1:{port}  (routes: {', '.join(sorted(ROUTES))})")
    server.serve_forever()


if __name__ == "__main__":
    serve()
