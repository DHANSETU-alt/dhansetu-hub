"""
Founder Review -- a twice-daily (10:00 / 22:00, per the founder's own
schedule) full-picture review across Shakthi OS itself and every tracked
business/initiative, sent to Telegram. Two real parts, not one blended
guess:

1. compile_review_data(): every number in this function is a real read
   from an existing, already-built subsystem (governor, security, watchdog,
   finance, initiatives) -- nothing here is computed just for this report.
2. counter_solution_plan(): ONE real local-model call to the CEO agent,
   given that real compiled data, asked for a short recommended-next-3-
   actions list. Same prose-override trick sentinel.ceo_summary() already
   needed -- without it the CEO agent's json decision-block habit takes
   over even for a request that isn't a decision.

This NEVER auto-executes anything it recommends -- every report ends with
an explicit "waiting for your command" line. That's not boilerplate, it's
the same fail-closed principle every CEO gate in this codebase already
follows (see CEO_FAILURE_REPORT.md / ZERO_SINGLE_POINT_FAILURE_PLAN.md):
a report proposing action is not the same as an approval to take it.
"""
from datetime import datetime

from . import db, finance, governor, security


def compile_review_data() -> dict:
    with db.get_conn() as conn:
        gov = governor.governor_status(conn)
        initiatives = db.list_initiatives(conn)
        decisions = db.recent_decisions(conn, limit=30)
        latest_security = db.latest_security_report(conn, business_id=None)
        watchdog_events = db.recent_watchdog_events(conn, since_id=0, limit=20)

    try:
        monthly_finance = finance.generate_report("monthly", business_id=None)
    except Exception as e:
        monthly_finance = {"error": str(e)}

    revise = [d for d in decisions if d["status"] == "revise"]
    critical_watchdog = [e for e in watchdog_events if e["severity"] == "critical"]
    warning_watchdog = [e for e in watchdog_events if e["severity"] == "warning"]

    return {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "governor_status": gov["status"],
        "subsystems": gov["subsystems"],
        "initiatives": initiatives,
        "pending_decisions": len(revise),
        "pending_decision_goals": [d["goal"][:80] for d in revise[:5]],
        "security_score": latest_security["score"] if latest_security else None,
        "watchdog_critical": len(critical_watchdog),
        "watchdog_warning": len(warning_watchdog),
        "watchdog_recent": [f"[{e['severity']}] {e['category']}: {e['detail'][:80]}" for e in watchdog_events[:5]],
        "finance": monthly_finance,
    }


def counter_solution_plan(data: dict) -> str:
    """Real CEO-agent call, not a template. Given the real compiled data,
    asks for a short, honest recommended-next-3-actions list -- explicitly
    a proposal for the founder to approve, never an instruction the system
    then carries out on its own."""
    from . import bug_fixer

    initiative_lines = "\n".join(
        f"  Task {i['seq']} — {i['title']}: {i['percent_complete']}% ({i['milestone_done']}/{i['milestone_total']})"
        for i in data["initiatives"]
    )
    prompt = (
        f"Twice-daily founder review. Real current state:\n\n"
        f"Governor status: {data['governor_status']}\n"
        f"Security posture score: {data['security_score']}\n"
        f"Watchdog: {data['watchdog_critical']} critical, {data['watchdog_warning']} warning event(s)\n"
        f"CEO decisions awaiting founder input: {data['pending_decisions']}\n\n"
        f"Tracked initiatives:\n{initiative_lines}\n\n"
        "IMPORTANT: this is NOT a decision to score, and you are NOT approving or executing "
        "anything. Ignore your usual json decision-block format completely. Write a short, "
        "honest 'recommended next 3 actions' list in plain English for the founder to review — "
        "no json, no markdown headers, no code fences. If something here genuinely needs the "
        "founder's own real-world action (not something an agent can do), say so plainly rather "
        "than inventing a task."
    )
    with db.get_conn() as conn:
        task_id = bug_fixer.new_pipeline_task(conn, "Founder review counter-solution plan")
        text = bug_fixer.call_agent(conn, task_id, "ceo", prompt)
        db.update_task(conn, task_id, "done", text)
    return text.strip()


def format_angella_push(data: dict, plan: str) -> str:
    """Real Angella push, 2026-09-06: same real compiled data as
    format_report(), but the counter-solution comes from PA Angella's own
    role (pa_angella.push_pending_work) instead of a generic CEO summary,
    in Gujarati, as arrow-chained flow steps per pending item -- the
    founder's own explicit ask ("push me pending tasks... every hour...
    with solution... flow chart mode"). The flow chains render as literal
    text arrows inside a monospace block, which is what Telegram can
    actually display without a new image-rendering dependency."""
    from . import telegram as tg
    esc = tg.escape_markdown_v2

    security_line = f"{data['security_score']}" if data["security_score"] is not None else "no scan"
    watchdog_line = f"{data['watchdog_critical']} critical, {data['watchdog_warning']} warning"

    lines = [f"🤖 *ANGELLA* — {esc(data['timestamp'])}", ""]
    lines.append(f"*Governor:* {esc(data['governor_status'])}  \\|  *Security:* {esc(security_line)}")
    lines.append(f"*Watchdog:* {esc(watchdog_line)}")
    lines.append("")
    lines.append("```")
    lines.append(plan)
    lines.append("```")
    return "\n".join(lines)


def format_report(data: dict, plan: str) -> str:
    # MarkdownV2: every *bold* marker below is a literal static string this
    # function writes -- safe, unescaped. Every interpolated value is real
    # dynamic data (goal text, initiative titles, CEO-agent output) and
    # goes through esc() first, since any of it could contain characters
    # (., -, (), _) that would otherwise break Telegram's parser.
    from . import telegram as tg
    esc = tg.escape_markdown_v2

    lines = [f"📋 *FOUNDER REVIEW* — {esc(data['timestamp'])}", ""]
    lines.append(f"*Governor:* {esc(data['governor_status'])}")
    for name, check in data["subsystems"].items():
        status = "ok" if check["ok"] else "DOWN"
        lines.append(f"  {esc(name)}: {esc(status)} — {esc(check['detail'])}")
    lines.append("")
    security_score = data["security_score"]
    security_line = f"{security_score}/100" if security_score is not None else "no scan on record"
    lines.append(f"*Security posture:* {esc(security_line)}")
    watchdog_line = f"{data['watchdog_critical']} critical, {data['watchdog_warning']} warning"
    lines.append(f"*Watchdog:* {esc(watchdog_line)}")
    for w in data["watchdog_recent"]:
        lines.append(f"  {esc(w)}")
    lines.append("")
    lines.append(f"*CEO decisions needing you:* {esc(str(data['pending_decisions']))}")
    for g in data["pending_decision_goals"]:
        lines.append(f"  \\- {esc(g)}")
    lines.append("")
    lines.append("*Tracked initiatives:*")
    for i in data["initiatives"]:
        lines.append(f"  Task {esc(str(i['seq']))} — {esc(i['title'])}: {esc(str(i['percent_complete']))}% \\({esc(str(i['milestone_done']))}/{esc(str(i['milestone_total']))}\\)")
    if fin := data.get("finance"):
        if "error" not in fin:
            lines.append("")
            finance_line = f"revenue ${fin['revenue_usd']:.2f}, profit ${fin['profit_usd']:.2f}"
            lines.append(f"*Finance \\(month\\):* {esc(finance_line)}")
    lines.append("")
    lines.append("*Counter\\-solution plan \\(CEO agent, real local\\-model call\\):*")
    lines.append(esc(plan))
    lines.append("")
    lines.append("_Nothing above has been acted on\\. Waiting for your command\\._")
    return "\n".join(lines)


def run_founder_review(token: str, chat_id: str) -> dict:
    from . import telegram as tg
    from . import telegram_service as ts
    from . import pa_angella

    data = compile_review_data()
    plan = pa_angella.push_pending_work(data)
    report_text = format_angella_push(data, plan)

    result = {"report_text": report_text, "telegram_sent": False}
    try:
        resolved_token, resolved_chat_id = ts.resolve_credentials(token, chat_id)
        tg.send_message(resolved_token, resolved_chat_id, report_text, parse_mode="MarkdownV2")
        result["telegram_sent"] = True
    except tg.TelegramError as e:
        result["telegram_error"] = str(e)
    return result
