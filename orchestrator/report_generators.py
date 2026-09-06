"""
Builds the text for each daily report. Every number here comes from a real
table (cost_ledger, decisions, tasks, tool_calls, finance_entries, sites) --
nothing is synthesized. Where a metric genuinely isn't available yet (SSL
status, live uptime -- there are no deployed URLs to check, only locally
generated files), the report says so plainly instead of faking a value.
"""
import os
from pathlib import Path

from . import db, finance, security


def ceo_report(business_id=None) -> str:
    with db.get_conn() as conn:
        decisions = db.recent_decisions(conn, limit=5)
        tasks = db.recent_tasks(conn, limit=50)

    if business_id is not None:
        tasks = [t for t in tasks if t["business_id"] == business_id]

    done = sum(1 for t in tasks if t["status"] == "done")
    failed = sum(1 for t in tasks if t["status"] == "failed")
    escalated_critical = sum(1 for t in tasks if t["risk_level"] == "critical")

    lines = ["*SHAKTHI CEO REPORT*", ""]
    lines.append(f"Tasks (last {len(tasks)}): {done} done, {failed} failed, {escalated_critical} critical-risk")
    lines.append("")
    lines.append("*Recent Decisions:*")
    if not decisions:
        lines.append("  (none yet)")
    for d in decisions:
        lines.append(f"  #{d['id']} [{d['status']}] p={d['priority_score']} r={d['risk_score']} "
                      f"i={d['business_impact_score']} — {d['goal'][:60]}")

    lines.append("")
    lines.append("*Recommended Actions:*")
    revise = [d for d in decisions if d["status"] == "revise"]
    if revise:
        lines.append(f"  - {len(revise)} decision(s) need founder input (unparseable or underspecified)")
    if failed:
        lines.append(f"  - {failed} recent task(s) failed — check `--audit` and task_events")
    if not revise and not failed:
        lines.append("  - nothing blocking right now")

    return "\n".join(lines)


def finance_report_text(business_id=None) -> str:
    daily = finance.generate_report("daily", business_id=business_id)
    monthly = finance.generate_report("monthly", business_id=business_id)

    lines = ["*SHAKTHI FINANCE REPORT*", ""]
    lines.append(f"Revenue today:  ${daily['revenue_usd']:.2f}")
    lines.append(f"Revenue month:  ${monthly['revenue_usd']:.2f}")
    lines.append(f"Expenses:       ${monthly['expense_usd']:.2f}")
    lines.append(f"Profit (mo):    ${monthly['profit_usd']:.2f}")
    lines.append(f"AI spend (mo):  ${monthly['api_cost_usd']:.4f}  ({monthly['ollama_calls']} ollama calls)")
    lines.append(f"Ollama savings: ${monthly['ollama_estimated_savings_usd']:.4f} vs. running those calls on Claude")
    return "\n".join(lines)


def security_report_text(business_id=None) -> str:
    r = security.review(business_id=business_id)
    lines = ["*SHAKTHI SECURITY REPORT*", ""]
    lines.append(f"Score: {r['score']}/100")
    lines.append(f"Findings: {len(r['findings'])}")
    for f in r["findings"][:10]:
        lines.append(f"  - [{f['type']}] {f['check']}: {f.get('file') or f.get('agent') or ''}")
    lines.append("")
    lines.append("SSL status / live uptime: not available — no deployed URLs exist yet, "
                  "only locally generated site files (see Website Health report)")
    return "\n".join(lines)


def agent_health_report_text() -> str:
    with db.get_conn() as conn:
        agents = db.list_agents(conn)
        tasks = db.recent_tasks(conn, limit=200)

    lines = ["*SHAKTHI AGENT HEALTH REPORT*", ""]
    for a in agents:
        agent_tasks = [t for t in tasks if t["agent_id"] == a["id"]]
        failed = sum(1 for t in agent_tasks if t["status"] == "failed")
        lines.append(f"  {a['id']:18s} {len(agent_tasks):3d} recent tasks, {failed} failed")
    return "\n".join(lines)


def cost_ledger_report_text() -> str:
    with db.get_conn() as conn:
        rows = db.cost_summary(conn)
    lines = ["*SHAKTHI COST LEDGER REPORT*", ""]
    if not rows:
        lines.append("  (no calls logged yet)")
    for r in rows:
        lines.append(f"  {r['provider']:8s} calls={r['calls']:4d} cost=${r['cost_usd']:.4f}")
    return "\n".join(lines)


def website_health_report_text() -> str:
    with db.get_conn() as conn:
        sites = conn.execute("SELECT * FROM sites WHERE status != 'planned'").fetchall()
        sites = [dict(s) for s in sites]

    lines = ["*SHAKTHI WEBSITE HEALTH REPORT*", ""]
    lines.append("No live deployment exists yet — this checks local file presence only, "
                  "not real uptime/SSL (see Known gaps in README).")
    lines.append("")
    ok, missing = 0, 0
    for s in sites:
        exists = bool(s["local_path"] and Path(s["local_path"]).exists())
        ok += exists
        missing += not exists
    lines.append(f"Generated sites: {len(sites)}  ({ok} file present, {missing} missing)")
    for s in sites[:10]:
        exists = bool(s["local_path"] and Path(s["local_path"]).exists())
        lines.append(f"  {s['domain']:30s} {'OK' if exists else 'MISSING'}")
    return "\n".join(lines)


ALL_REPORTS = {
    "ceo": ceo_report,
    "finance": finance_report_text,
    "security": security_report_text,
    "agent_health": agent_health_report_text,
    "cost_ledger": cost_ledger_report_text,
    "website_health": website_health_report_text,
}
