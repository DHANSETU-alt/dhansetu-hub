import argparse
import json
import sys
from pathlib import Path

from . import access, alerts, audit, bug_fixer, buddy, ceo, config, correction_bot, db, finance, knowledge, registry, routing, security, sentinel, sheets, sitegen, template_registry, voice, voice_history, website_audit, website_builder
from . import telegram as tg
from . import telegram_service as ts
from .tools.registry import TOOL_REGISTRY


def _cmd_init():
    db.init_db()
    agents = registry.sync_registry()
    print(f"DB ready at {config.DB_PATH}")
    print(f"Registered {len(agents)} agents: {', '.join(a['id'] for a in agents)}")


def _cmd_list_agents():
    with db.get_conn() as conn:
        rows = db.list_agents(conn)
    for r in rows:
        tools = ", ".join(json.loads(r["allowed_tools"] or "[]")) or "(none)"
        print(f"{r['id']:20s} layer={r['layer']:12s} tier={r['default_model_tier']:6s} "
              f"scope={r['allowed_scope']:14s} tools={tools}")


def _cmd_list_tools():
    for name, spec in TOOL_REGISTRY.items():
        print(f"{name:14s} risk={spec['risk_tier']:10s} {spec['description']}")
    print(f"\nSHAKTHI_ALLOW_EXEC={'1 (dangerous-tier tools enabled)' if config.ALLOW_EXEC else '0 (dangerous-tier tools blocked)'}")
    print(f"SHAKTHI_TOOLS_DRY_RUN={'1' if config.TOOLS_DRY_RUN else '0'}")


def _cmd_costs():
    with db.get_conn() as conn:
        for row in db.cost_summary(conn):
            print(f"{row['provider']:8s} calls={row['calls']:4d} tokens_in={row['tokens_in']:7d} "
                  f"tokens_out={row['tokens_out']:7d} cost_usd=${row['cost_usd']:.4f}")


def _cmd_audit(limit: int):
    with db.get_conn() as conn:
        for c in db.recent_tool_calls(conn, limit=limit):
            note = c["denial_reason"] or c["output_summary"] or ""
            print(f"[{c['created_at']}] task={c['task_id']:<4} agent={c['agent_id']:16s} "
                  f"tool={c['tool_name']:12s} decision={c['decision']:8s} {note[:80]}")


def _cmd_generate_site(business_id: int, template_id: str):
    result = sitegen.generate_site(business_id, template_id=template_id)
    print(f"Site generated: {result['local_path']}")
    print(f"site_id={result['site_id']} task_id={result['task_id']} template={result['template_id']}")


def _cmd_decide(goal: str, business_id):
    result = ceo.decide(goal, business_id=business_id)
    print(f"[decision {result['decision_id']}] status={result['status']}")
    print(f"priority={result['priority_score']} risk={result['risk_score']} "
          f"business_impact={result['business_impact_score']}")
    print(f"reason: {result['reason']}")


def _cmd_finance_report(period: str, business_id):
    r = finance.generate_report(period, business_id=business_id)
    print(f"Finance report ({period}, since {r['since']})" + (f" — business {business_id}" if business_id else " — all businesses"))
    print(f"  revenue:  ${r['revenue_usd']:.2f}")
    print(f"  expense:  ${r['expense_usd']:.2f}")
    print(f"  api cost: ${r['api_cost_usd']:.4f}  ({r['ollama_calls']} ollama calls, "
          f"~${r['ollama_estimated_savings_usd']:.4f} saved vs. running them on Claude)")
    print(f"  profit:   ${r['profit_usd']:.2f}")


def _cmd_finance_entry(type_: str, amount: float, business_id: int, note: str, category: str,
                        telegram_token=None, telegram_chat_id=None):
    with db.get_conn() as conn:
        entry_id = db.insert_finance_entry(conn, business_id, type_, amount, note, category=category)
    print(f"Logged finance_entry {entry_id}: {type_}/{category} ${amount:.2f} for business {business_id}")

    if type_ == "revenue":
        try:
            token, chat_id = ts.resolve_credentials(telegram_token, telegram_chat_id)
            ts.alert(token, chat_id, "revenue", f"New revenue logged: ${amount:.2f} (business {business_id}) — {note}")
            print("Telegram revenue alert sent.")
        except tg.TelegramError:
            pass  # no credentials configured for this invocation -- not an error, just skip the alert
        finally:
            # Mark this entry seen either way -- a later --alerts-sweep must
            # not re-alert on it. Found live: without this, one revenue
            # entry produced two separate Telegram notifications.
            alerts.mark_revenue_seen(entry_id)


def _cmd_telegram_test(token, chat_id):
    token, chat_id = ts.resolve_credentials(token, chat_id)
    me = tg.get_me(token)
    print(f"Bot OK: @{me.get('username')} ({me.get('first_name')})")
    tg.send_message(token, chat_id, "Shakthi AI OS: test message. If you see this, credentials are correct.")
    print(f"Sent a test message to chat_id={chat_id}")


def _cmd_telegram_send(report, token, chat_id, business_id):
    token, chat_id = ts.resolve_credentials(token, chat_id)
    if report == "all":
        results = ts.send_daily_reports(token, chat_id, business_id=business_id)
        for name, result in results:
            print(f"  {name:16s} {'ok' if 'error' not in result else 'FAILED: ' + result['error']}")
    else:
        ts.send_report(report, token, chat_id, business_id=business_id)
        print(f"Sent '{report}' report to chat_id={chat_id}")


def _cmd_telegram_alert(message, category, token, chat_id):
    token, chat_id = ts.resolve_credentials(token, chat_id)
    ts.alert(token, chat_id, category, message)
    print("Alert sent.")


def _cmd_telegram_poll(token, chat_id):
    token, chat_id = ts.resolve_credentials(token, chat_id)
    ts.poll_forever(token, chat_id)


def _cmd_sheets_sync(credentials_path, spreadsheet_id, period, tax_rate):
    if not credentials_path or not spreadsheet_id:
        print("--sheets-sync requires --sheets-credentials <path> and --sheets-id <id>", file=sys.stderr)
        sys.exit(1)
    result = sheets.sync_all(credentials_path, spreadsheet_id, period=period, tax_rate=tax_rate)
    print(f"Sheets sync complete ({period}, tax_rate={tax_rate}):")
    for name, r in result.items():
        print(f"  {name}: {r}")
    print(f"\nView: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")


def _cmd_alerts_sweep(token, chat_id):
    token, chat_id = ts.resolve_credentials(token, chat_id)
    sent = alerts.run_sweep(token, chat_id)
    total = sum(sent.values())
    print(f"Alert sweep complete: {total} alert message(s) sent")
    for category, count in sent.items():
        print(f"  {category}: {count}")


def _cmd_bug_report(title, description, severity):
    bug_id = bug_fixer.report_bug(title, description, severity=severity)
    print(f"Filed bug #{bug_id} [{severity}]: {title}")


def _cmd_bug_scan():
    candidates = bug_fixer.scan_for_bugs()
    if not candidates:
        print("No new bug candidates found in task/error logs.")
        return
    print(f"{len(candidates)} candidate(s) found:")
    for c in candidates:
        print(f"  [{c['source']}] {c['title']}")
    print("\nRun --bug-analyze-scan to create + analyze all of them, or file individually.")


def _cmd_bug_analyze_scan():
    candidates = bug_fixer.scan_for_bugs()
    for c in candidates:
        result = bug_fixer.create_and_analyze(c)
        note = f"recurrence of #{result['recurrence_of']}" if result.get("recurrence_of") else result.get("severity", "?")
        print(f"  bug #{result['bug_id']}: {note}")
    print(f"{len(candidates)} candidate(s) processed.")


def _cmd_bug_analyze(bug_id):
    result = bug_fixer.analyze_bug(bug_id)
    print(json.dumps(result, indent=2))


def _cmd_bug_propose(bug_id):
    result = bug_fixer.propose_patch(bug_id)
    print(f"Patch #{result['patch_id']} staged: {result['patch_path']}")
    if result.get("diff_path"):
        print(f"Diff: {result['diff_path']}")


def _cmd_bug_review(bug_id):
    result = bug_fixer.run_full_review_pipeline(bug_id)
    print(f"Pipeline stopped at: {result['stage']}  approved={result['approved']}")
    print(json.dumps(result["detail"], indent=2, default=str))


def _cmd_bugfix_apply(bug_id, confirm):
    result = bug_fixer.apply_patch(bug_id, confirm=confirm)
    print(f"Applied patch to {result['target']}")
    print(f"Backup: {result['backup']}")


def _cmd_bugfix_test(bug_id):
    result = bug_fixer.run_tests(bug_id)
    print(f"Tests {'PASSED' if result['passed'] else 'FAILED'}")
    print(result["output"][-2000:])


def _cmd_bug_list(status, severity):
    with db.get_conn() as conn:
        bugs = db.list_bugs(conn, status=status, severity=severity, limit=50)
    if not bugs:
        print("No bugs match.")
        return
    for b in bugs:
        print(f"#{b['id']:<4} [{b['severity']}] {b['status']:14s} occ={b['occurrence_count']} "
              f"reg={b['regression_count']:2d}  {b['title'][:60]}")


def _cmd_bug_report_detail(bug_id):
    print(bug_fixer.root_cause_report(bug_id))


def _cmd_patches(bug_id):
    with db.get_conn() as conn:
        patches = db.list_patches(conn, bug_id=bug_id)
    for p in patches:
        print(f"#{p['id']:<4} bug=#{p['bug_id']:<4} applied={bool(p['applied'])}  {p['target_file']}  ({p['created_at']})")
        if p["diff_path"]:
            print(f"      diff: {p['diff_path']}")


def _cmd_audit_run(deepen_top_n):
    print(f"Running full codebase audit (deepening top {deepen_top_n} findings)... this calls local models several times and may take several minutes.")
    result = audit.run_full_audit(deepen_top_n=deepen_top_n)
    print(f"\nAudit #{result['audit_id']} complete.")
    print(f"Severity score: {result['severity_score']}/100")
    print(f"Findings: {result['findings_count']} across {result['files_affected']} files")
    for cat, count in result["by_category"].items():
        print(f"  {cat}: {count}")
    print(f"Deepened into bugs: {result['deepened_bugs']}")
    print(f"\nExecutive summary:\n{result['executive_summary']}")


def _cmd_sentinel_check():
    h = sentinel.collect_health()
    print(f"Health: {h['health_score']}/100   Performance: {h['performance_score']}/100")
    print(f"  CPU: {h['cpu_percent']}%  ({h['cpu_freq_mhz']} MHz)  temp: {h['cpu_temp_c'] if h['cpu_temp_c'] is not None else 'unavailable (needs sudo)'}")
    print(f"  RAM: {h['ram_percent']}%   Swap: {h['swap_percent']}%   Disk: {h['disk_percent']}%")
    if h["battery_percent"] is not None:
        print(f"  Battery: {h['battery_percent']}% ({'plugged in' if h['battery_plugged'] else 'on battery'})")
    print(f"  Internet: {'OK' if h['internet_ok'] else 'DOWN'}   Ollama: {'OK' if h['ollama_ok'] else 'DOWN'}   DB: {'OK' if h['db_ok'] else 'DOWN'}")
    print(f"  Active tasks: {h['active_tasks']}   Untriaged errors: {h['untriaged_errors']}")
    print()
    for name, status in sentinel.service_status().items():
        print(f"  {name}: {status}")


def _cmd_sentinel_loop(interval_seconds: int, telegram_token, telegram_chat_id):
    """Fills the one documented Sentinel gap: --sentinel-check was one-shot
    only. Foreground loop -- run under `caffeinate`/launchd/a background
    shell for real continuous monitoring, same pattern the rest of this
    system uses for anything recurring (cron for scheduled_reports.py, not
    a bespoke daemon)."""
    import time
    print(f"Sentinel loop: collecting every {interval_seconds}s (Ctrl+C to stop)...")
    while True:
        h = sentinel.collect_health()
        print(f"[{h.get('created_at', '')}] health={h['health_score']} perf={h['performance_score']} "
              f"cpu={h['cpu_percent']}% ram={h['ram_percent']}% disk={h['disk_percent']}%")
        if telegram_token or telegram_chat_id:
            try:
                token, chat_id = ts.resolve_credentials(telegram_token, telegram_chat_id)
                sent = alerts.run_sweep(token, chat_id)
                if sent.get("sentinel"):
                    print(f"  -> {sent['sentinel']} Sentinel alert(s) sent")
            except tg.TelegramError:
                pass  # no credentials for this invocation -- loop still runs, just no alerting
        time.sleep(interval_seconds)


def _cmd_ops_scan(telegram_token, telegram_chat_id, sheets_credentials, sheets_id):
    print("OPS-001: Sentinel -> CEO -> Telegram live system health scan...")
    result = sentinel.run_ops_scan(telegram_token, telegram_chat_id, sheets_credentials, sheets_id)
    print()
    print(result["report_text"])
    print()
    print(f"Telegram sent: {result['telegram_sent']}" + (f" (error: {result.get('telegram_error')})" if result.get("telegram_error") else ""))
    print(f"Sheets synced: {result['sheets_synced']}" + (f" ({result.get('sheets_error')})" if result.get("sheets_error") else ""))
    print("DB stored: True (every health snapshot is always written to system_health)")


def _cmd_security_scan(telegram_token, telegram_chat_id, sheets_credentials, sheets_id):
    print("OPS-002: Security posture scan (API keys, env vars, file permissions, credentials)...")
    result = security.security_posture_scan(telegram_token, telegram_chat_id, sheets_credentials, sheets_id)
    print()
    print(result["report_text"])
    print()
    print(f"Telegram sent: {result['telegram_sent']}" + (f" (error: {result.get('telegram_error')})" if result.get("telegram_error") else ""))
    print(f"Sheets synced: {result['sheets_synced']}" + (f" ({result.get('sheets_error')})" if result.get("sheets_error") else ""))
    print("DB stored: True (security_reports, business_id=NULL for platform-wide scan)")


def _cmd_website_audit(url, telegram_token, telegram_chat_id, sheets_credentials, sheets_id):
    print(f"WEB-001: Auditing {url} ...")
    result = website_audit.run_website_audit(url, telegram_token, telegram_chat_id, sheets_credentials, sheets_id)
    print()
    print(result["report_text"])
    print()
    print(f"Findings: {result['findings_count']} across {result['pages_checked']} pages/resources checked")
    print(f"Telegram sent: {result['telegram_sent']}" + (f" (error: {result.get('telegram_error')})" if result.get("telegram_error") else ""))
    print(f"Sheets synced: {result['sheets_synced']}" + (f" ({result.get('sheets_error')})" if result.get("sheets_error") else ""))
    print(f"DB stored: True (audits #{result['audit_id']}, audit_findings)")


def _cmd_correct(task_type, task_ref, content_file, telegram_token, telegram_chat_id, sheets_credentials, sheets_id):
    content = Path(content_file).read_text()
    print(f"Correction Bot reviewing {task_type} content from {content_file} ...")
    result = correction_bot.review_and_correct(task_type, task_ref, content, telegram_token=telegram_token,
                                                telegram_chat_id=telegram_chat_id,
                                                sheets_credentials=sheets_credentials, sheets_id=sheets_id)
    print()
    print(result["report_text"])
    print()
    print(f"Telegram sent: {result['telegram_sent']}" + (f" (error: {result.get('telegram_error')})" if result.get("telegram_error") else ""))
    print(f"Sheets synced: {result['sheets_synced']}" + (f" ({result.get('sheets_error')})" if result.get("sheets_error") else ""))
    print(f"DB stored: True (corrections #{result['correction_id']}, correction_findings)")


def _cmd_correction_history(limit):
    with db.get_conn() as conn:
        rows = db.list_corrections(conn, limit=limit)
    if not rows:
        print("No corrections logged yet.")
        return
    for r in rows:
        print(f"#{r['id']} [{r['status']}] {r['task_type']} · {r['task_ref'] or '(no ref)'} · "
              f"correction={r['correction_score']} quality={r['quality_score']} "
              f"issues={r['issues_found']}/{r['issues_fixed']} fixed · final={r['final_status']} · {r['created_at']}")


def _cmd_knowledge_add(category, title, content, tags):
    doc_id = knowledge.add_document(category, title, content, tags)
    print(f"Added knowledge document #{doc_id}: {title}")


def _cmd_knowledge_ask(question, category):
    result = knowledge.ask(question, category=category)
    print(result["answer"])
    if result["sources"]:
        print(f"\nSources: {', '.join(result['sources'])}")


def _cmd_buddy_chat(message, mode, session_id):
    result = buddy.chat(session_id, mode, message)
    print(result["response"])
    if result["blocked"]:
        print(f"[Safe Mode triggered: {result['blocked_reason']}]", file=sys.stderr)


def _cmd_voice_listen(seconds, owner_passphrase):
    result = voice.listen_and_execute(seconds=seconds, identity_passphrase=owner_passphrase)
    print(f"Heard ({result['identity']}, {result['language']}): {result['transcript']}")
    print(f"Routed to: {result['intent']['category']}/{result['intent']['action']}")
    if result.get("ceo_status"):
        print(f"CEO review: {result['ceo_status']}")
    print(f"Result: {result['result']}")


def _cmd_voice_history(limit):
    print(voice_history.format_report(limit))


def _cmd_website_templates():
    for name, fn in template_registry.TEMPLATES.items():
        print(f"  {name:16s} {fn.__doc__ or ''}")


def _cmd_website_build(business_id, site_type, request_text):
    print(f"Running full website pipeline (site_type={site_type})... calls local models several times, may take a few minutes.")
    result = website_builder.run_full_pipeline(business_id, site_type, request_text)
    print(f"\nProject #{result['project_id']} stopped at stage: {result['stage']}  ok={result['ok']}")
    print(json.dumps(result["detail"], indent=2, default=str))


def _cmd_website_projects(status):
    with db.get_conn() as conn:
        projects = db.list_website_projects(conn, status=status, limit=50)
    if not projects:
        print("No website projects yet.")
        return
    for p in projects:
        print(f"#{p['id']:<4} [{p['site_type']:16s}] {p['status']:16s} biz={p['business_id']}  {p['founder_request'][:50]}")


def _cmd_security_review(business_id):
    r = security.review(business_id=business_id)
    print(f"Security score: {r['score']}/100 ({len(r['findings'])} findings)")
    for f in r["findings"]:
        print(f"  - [{f['type']}] {f['check']}: {f.get('file') or f.get('agent') or ''}")


def _cmd_dashboard():
    with db.get_conn() as conn:
        active = db.active_task_count(conn)
        tasks = db.recent_tasks(conn, limit=8)
        agents = db.list_agents(conn)
        decisions = db.recent_decisions(conn, limit=5)
        denied = db.recent_tool_calls(conn, limit=5, decision="denied")
        costs = db.cost_summary(conn)
        businesses = db.list_businesses(conn)

    print("=" * 60)
    print("SHAKTHI AI OS — Dashboard  (CLI report, not a web UI — see README)")
    print("=" * 60)

    print(f"\nBusinesses: {len(businesses)}   Active tasks: {active}   Registered agents: {len(agents)}")

    print("\n-- Agent Status --")
    for a in agents:
        print(f"  {a['id']:20s} layer={a['layer']:12s} tier={a['default_model_tier']}")

    print("\n-- Recent Tasks --")
    for t in tasks:
        print(f"  #{t['id']:<4} {t['agent_id']:16s} biz={str(t['business_id']):4s} "
              f"status={t['status']:8s} risk={t['risk_level']}")

    print("\n-- Cost Ledger --")
    if not costs:
        print("  (no calls logged yet)")
    for c in costs:
        print(f"  {c['provider']:8s} calls={c['calls']:4d} cost_usd=${c['cost_usd']:.4f}")

    print("\n-- Finance Summary --")
    for b in businesses:
        r = finance.generate_report("monthly", business_id=b["id"])
        if r["revenue_usd"] or r["expense_usd"]:
            print(f"  {b['name']:14s} profit=${r['profit_usd']:.2f} (revenue ${r['revenue_usd']:.2f}, expense ${r['expense_usd']:.2f})")

    print("\n-- Security Alerts (recent denied tool calls) --")
    if not denied:
        print("  (none)")
    for d in denied:
        print(f"  agent={d['agent_id']:16s} tool={d['tool_name']:12s} {d['denial_reason']}")

    print("\n-- CEO Decisions --")
    if not decisions:
        print("  (none yet)")
    for d in decisions:
        print(f"  #{d['id']:<4} status={d['status']:9s} priority={d['priority_score']} "
              f"risk={d['risk_score']} impact={d['business_impact_score']}  {d['goal'][:50]}")
    print()


def main():
    parser = argparse.ArgumentParser(prog="shakthi", description="Shakthi AI OS — local orchestrator")
    parser.add_argument("goal", nargs="?", help="What you want the agent to do")
    parser.add_argument("--agent", default="manager", help="Agent id (see --list-agents)")
    parser.add_argument("--business", type=int, default=None, help="business_id to scope this task to")

    parser.add_argument("--init", action="store_true", help="Initialize the DB and sync the agent registry")
    parser.add_argument("--list-agents", action="store_true")
    parser.add_argument("--list-tools", action="store_true")
    parser.add_argument("--costs", action="store_true", help="Print cost ledger summary and exit")
    parser.add_argument("--audit", nargs="?", const=20, type=int, metavar="LIMIT", help="Print recent tool_calls audit log")
    parser.add_argument("--dashboard", action="store_true", help="Print the CLI dashboard report")

    parser.add_argument("--generate-site", action="store_true", help="Deterministically generate a site for --business")
    parser.add_argument("--template", default="template_landing_v1")

    parser.add_argument("--decide", metavar="GOAL", help="Run the CEO agent's decision workflow on a goal")

    parser.add_argument("--finance-report", choices=["daily", "weekly", "monthly", "quarterly", "yearly"])
    parser.add_argument("--finance-entry", choices=["revenue", "expense"])
    parser.add_argument("--amount", type=float)
    parser.add_argument("--note", default="")
    parser.add_argument("--category", default="general", help="e.g. general, marketing, hosting, tools, payroll")

    parser.add_argument("--security-review", action="store_true")

    parser.add_argument("--telegram-token", help="Manual entry — not stored anywhere")
    parser.add_argument("--telegram-chat-id", help="Manual entry — not stored anywhere")
    parser.add_argument("--telegram-test", action="store_true", help="Verify credentials and send a test message")
    parser.add_argument("--telegram-send", metavar="REPORT",
                         help="ceo|finance|security|agent_health|cost_ledger|website_health|all")
    parser.add_argument("--telegram-alert", metavar="MESSAGE")
    parser.add_argument("--telegram-alert-category", default="general")
    parser.add_argument("--telegram-poll", action="store_true", help="Run the /command bot (foreground, long-polling)")

    parser.add_argument("--sheets-sync", action="store_true", help="Sync all 8 tabs to Google Sheets")
    parser.add_argument("--sheets-credentials", help="Path to a Google service account JSON key — manual entry, not stored")
    parser.add_argument("--sheets-id", help="Target spreadsheet ID — manual entry, not stored")
    parser.add_argument("--sheets-period", choices=["daily", "weekly", "monthly", "quarterly", "yearly"], default="monthly")
    parser.add_argument("--tax-rate", type=float, default=None, help="Fraction, e.g. 0.18 — defaults to SHAKTHI_DEFAULT_TAX_RATE (0.18)")

    parser.add_argument("--alerts-sweep", action="store_true", help="Check all alert categories and send only what's new to Telegram")

    parser.add_argument("--bug-report", metavar="TITLE", help="Manually file a bug")
    parser.add_argument("--description", default="")
    parser.add_argument("--severity", choices=["P0", "P1", "P2", "P3", "P4"], default="P2")
    parser.add_argument("--bug-scan", action="store_true", help="List new bug candidates from task/error logs")
    parser.add_argument("--bug-analyze-scan", action="store_true", help="Scan AND create+analyze every candidate")
    parser.add_argument("--bug-analyze", type=int, metavar="BUG_ID")
    parser.add_argument("--bug-propose", type=int, metavar="BUG_ID", help="Engineer proposes a staged patch")
    parser.add_argument("--bug-review", type=int, metavar="BUG_ID", help="Run propose->QA->Security->CEO in one call")
    parser.add_argument("--bugfix-apply", type=int, metavar="BUG_ID", help="Apply a CEO-approved patch to live source")
    parser.add_argument("--confirm", action="store_true", help="Required with --bugfix-apply")
    parser.add_argument("--bugfix-test", type=int, metavar="BUG_ID", help="Run the test suite, requires SHAKTHI_ALLOW_EXEC=1")
    parser.add_argument("--bug-list", action="store_true")
    parser.add_argument("--bug-status", default=None)
    parser.add_argument("--bug-detail", type=int, metavar="BUG_ID", help="Full root-cause report for one bug")
    parser.add_argument("--patches", action="store_true", help="List the patch registry")
    parser.add_argument("--patch-bug", type=int, metavar="BUG_ID", help="Filter --patches to one bug")

    parser.add_argument("--audit-run", action="store_true", help="Full codebase audit: CEO -> Security -> Bug Fixer -> Engineer -> CEO")
    parser.add_argument("--deepen", type=int, default=3, help="How many top findings to run through the full bug pipeline")

    parser.add_argument("--sentinel-check", action="store_true", help="Collect and print a real system health snapshot")
    parser.add_argument("--sentinel-loop", action="store_true", help="Continuous monitoring (foreground loop, Ctrl+C to stop)")
    parser.add_argument("--ops-scan", action="store_true", help="OPS-001: Sentinel -> CEO -> Telegram live health scan, stored in DB (+ Sheets if credentials given)")
    parser.add_argument("--security-scan", action="store_true", help="OPS-002: live security posture scan -> Telegram, stored in DB (+ Sheets if credentials given)")
    parser.add_argument("--website-audit", metavar="URL", help="WEB-001: live external website audit -> Telegram, stored in DB (+ Sheets if credentials given)")
    parser.add_argument("--correct", metavar="TASK_TYPE", choices=correction_bot.TASK_TYPES,
                         help=f"Correction Bot: review content from --content-file. Task types: {', '.join(correction_bot.TASK_TYPES)}")
    parser.add_argument("--content-file", help="path to the content file to review, used with --correct")
    parser.add_argument("--task-ref", default=None, help="free-text pointer to the source, used with --correct")
    parser.add_argument("--correction-history", nargs="?", const=20, type=int, metavar="N",
                         help="print the last N corrections (default 20)")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between --sentinel-loop collections")

    parser.add_argument("--knowledge-add", metavar="TITLE")
    parser.add_argument("--content", default="")
    parser.add_argument("--tags", default="")
    parser.add_argument("--knowledge-category", default="general")
    parser.add_argument("--knowledge-ask", metavar="QUESTION")

    parser.add_argument("--buddy-chat", metavar="MESSAGE")
    parser.add_argument("--buddy-mode", choices=["child", "family", "general"], default="general")
    parser.add_argument("--session-id", default="cli-session")

    parser.add_argument("--voice-listen", action="store_true", help="Record from the mic and route the command")
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument("--owner-passphrase", default=None, help="Manual entry — not stored anywhere")
    parser.add_argument("--voice-history", nargs="?", const=10, type=int, metavar="LIMIT", help="Print recent voice command history")

    parser.add_argument("--website-templates", action="store_true", help="List the 7 registered site types")
    parser.add_argument("--website-build", metavar="SITE_TYPE", help="Run the full pipeline: CEO -> Requirements -> Build -> QA -> Security -> Package")
    parser.add_argument("--request", default="", help="Founder request text for --website-build")
    parser.add_argument("--website-projects", action="store_true", help="List website projects")
    parser.add_argument("--project-status", default=None)

    args = parser.parse_args()
    try:
        return _dispatch(args)
    except (tg.TelegramError, sheets.SheetsError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Real error capture for the Bug Fixer's scan_for_bugs() to find --
        # not a simulated log. Re-raised after logging so the traceback
        # still reaches the terminal; this isn't meant to swallow bugs,
        # just make sure they're recorded before they scroll off-screen.
        import traceback as tb_mod
        with db.get_conn() as conn:
            db.log_error(conn, "cli", getattr(e, "__module__", "?"), str(e), tb_mod.format_exc())
        raise


def _dispatch(args):
    if args.init:
        return _cmd_init()
    if args.list_agents:
        return _cmd_list_agents()
    if args.list_tools:
        return _cmd_list_tools()
    if args.costs:
        return _cmd_costs()
    if args.audit is not None:
        return _cmd_audit(args.audit)
    if args.dashboard:
        return _cmd_dashboard()
    if args.generate_site:
        if args.business is None:
            print("--generate-site requires --business <id>", file=sys.stderr)
            sys.exit(1)
        return _cmd_generate_site(args.business, args.template)
    if args.decide:
        return _cmd_decide(args.decide, args.business)
    if args.finance_report:
        return _cmd_finance_report(args.finance_report, args.business)
    if args.finance_entry:
        if args.business is None or args.amount is None:
            print("--finance-entry requires --business <id> and --amount <n>", file=sys.stderr)
            sys.exit(1)
        return _cmd_finance_entry(args.finance_entry, args.amount, args.business, args.note, args.category,
                                   telegram_token=args.telegram_token, telegram_chat_id=args.telegram_chat_id)
    if args.security_review:
        return _cmd_security_review(args.business)
    if args.telegram_test:
        return _cmd_telegram_test(args.telegram_token, args.telegram_chat_id)
    if args.telegram_send:
        return _cmd_telegram_send(args.telegram_send, args.telegram_token, args.telegram_chat_id, args.business)
    if args.telegram_alert:
        return _cmd_telegram_alert(args.telegram_alert, args.telegram_alert_category, args.telegram_token, args.telegram_chat_id)
    if args.telegram_poll:
        return _cmd_telegram_poll(args.telegram_token, args.telegram_chat_id)
    if args.sheets_sync:
        tax_rate = args.tax_rate if args.tax_rate is not None else sheets.DEFAULT_TAX_RATE
        return _cmd_sheets_sync(args.sheets_credentials, args.sheets_id, args.sheets_period, tax_rate)
    if args.alerts_sweep:
        return _cmd_alerts_sweep(args.telegram_token, args.telegram_chat_id)
    if args.bug_report:
        return _cmd_bug_report(args.bug_report, args.description, args.severity)
    if args.bug_scan:
        return _cmd_bug_scan()
    if args.bug_analyze_scan:
        return _cmd_bug_analyze_scan()
    if args.bug_analyze:
        return _cmd_bug_analyze(args.bug_analyze)
    if args.bug_propose:
        return _cmd_bug_propose(args.bug_propose)
    if args.bug_review:
        return _cmd_bug_review(args.bug_review)
    if args.bugfix_apply:
        if not args.confirm:
            print("--bugfix-apply requires --confirm (this overwrites a real source file)", file=sys.stderr)
            sys.exit(1)
        return _cmd_bugfix_apply(args.bugfix_apply, args.confirm)
    if args.bugfix_test:
        return _cmd_bugfix_test(args.bugfix_test)
    if args.bug_list:
        return _cmd_bug_list(args.bug_status, None)
    if args.bug_detail:
        return _cmd_bug_report_detail(args.bug_detail)
    if args.patches:
        return _cmd_patches(args.patch_bug)
    if args.audit_run:
        return _cmd_audit_run(args.deepen)
    if args.sentinel_check:
        return _cmd_sentinel_check()
    if args.sentinel_loop:
        return _cmd_sentinel_loop(args.interval, args.telegram_token, args.telegram_chat_id)
    if args.ops_scan:
        return _cmd_ops_scan(args.telegram_token, args.telegram_chat_id, args.sheets_credentials, args.sheets_id)
    if args.security_scan:
        return _cmd_security_scan(args.telegram_token, args.telegram_chat_id, args.sheets_credentials, args.sheets_id)
    if args.website_audit:
        return _cmd_website_audit(args.website_audit, args.telegram_token, args.telegram_chat_id, args.sheets_credentials, args.sheets_id)
    if args.correct:
        if not args.content_file:
            print("--correct requires --content-file PATH")
            return
        return _cmd_correct(args.correct, args.task_ref, args.content_file, args.telegram_token,
                             args.telegram_chat_id, args.sheets_credentials, args.sheets_id)
    if args.correction_history is not None:
        return _cmd_correction_history(args.correction_history)
    if args.knowledge_add:
        return _cmd_knowledge_add(args.knowledge_category, args.knowledge_add, args.content, args.tags)
    if args.knowledge_ask:
        return _cmd_knowledge_ask(args.knowledge_ask, None)
    if args.buddy_chat:
        return _cmd_buddy_chat(args.buddy_chat, args.buddy_mode, args.session_id)
    if args.voice_listen:
        return _cmd_voice_listen(args.seconds, args.owner_passphrase)
    if args.voice_history is not None:
        return _cmd_voice_history(args.voice_history)
    if args.website_templates:
        return _cmd_website_templates()
    if args.website_build:
        if args.business is None:
            print("--website-build requires --business <id>", file=sys.stderr)
            sys.exit(1)
        return _cmd_website_build(args.business, args.website_build, args.request)
    if args.website_projects:
        return _cmd_website_projects(args.project_status)

    if not args.goal:
        parser.print_help()
        sys.exit(1)

    result = routing.run_task(args.agent, args.goal, business_id=args.business)
    print(f"[task {result['task_id']}] status={result['status']} escalated={result['escalated']}\n")
    print(result["output"])


if __name__ == "__main__":
    main()
