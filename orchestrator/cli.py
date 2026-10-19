import argparse
import json
import sys
from pathlib import Path

from . import access, alerts, audit, bug_fixer, buddy, ceo, chrome_developer, config, correction_bot, customer_success, db, dhansetu_ai, failure_analysis, finance, founder_review, incident_manager, incident_scheduler, initiatives, knowledge, team_register, load_manager, marketing, market_data, onboarding, pa_angella, payment_certification, payment_gateway_manager, payments, pdf_studio, peopledesk, pricing, prompt_engine, registry, routing, sales, security, sentinel, sheets, sitegen, skill_test, support_bot, template_registry, trading_engine, voice, voice_history, watchdog, website_audit, website_builder, worker_pool
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
        squad = r["squad"] or "(unassigned)"
        print(f"{r['id']:20s} squad={squad:16s} layer={r['layer']:12s} tier={r['default_model_tier']:6s} "
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


def _cmd_security_alert_check(token, chat_id):
    token, chat_id = ts.resolve_credentials(token, chat_id)
    sent = alerts.run_security_posture_check(token, chat_id)
    count = sent["security_posture"]
    print(f"Security posture alert check complete: {count} message(s) sent" if count
          else "Security posture alert check complete: no new drop to report")


def _cmd_founder_review(token, chat_id):
    token, chat_id = ts.resolve_credentials(token, chat_id)
    result = founder_review.run_founder_review(token, chat_id)
    print(result["report_text"])
    print()
    print("Telegram sent" if result["telegram_sent"] else f"Telegram NOT sent: {result.get('telegram_error')}")


def _cmd_domain_dns_check(token, chat_id):
    token, chat_id = ts.resolve_credentials(token, chat_id)
    sent = alerts.run_domain_dns_check(token, chat_id)
    count = sent["domain_dns"]
    print(f"Domain DNS check complete: {count} message(s) sent" if count
          else "Domain DNS check complete: not resolved yet (or already alerted)")


def _cmd_watchdog_scan():
    state = alerts._load_state()
    result = watchdog.run_scan(state)
    alerts._save_state(state)
    print(watchdog.format_report(result))


def _cmd_watchdog_alert_check(token, chat_id):
    token, chat_id = ts.resolve_credentials(token, chat_id)
    sent = alerts.run_watchdog_alert_check(token, chat_id)
    count = sent["watchdog"]
    print(f"Watchdog alert check complete: {count} message(s) sent" if count
          else "Watchdog alert check complete: nothing above info level to report")


def _cmd_sentinel_alert_check(token, chat_id):
    token, chat_id = ts.resolve_credentials(token, chat_id)
    sent = alerts.run_sentinel_alert_check(token, chat_id)
    count = sent["sentinel"]
    print(f"Sentinel alert check complete: {count} message(s) sent" if count
          else "Sentinel alert check complete: nothing to report")


def _cmd_live_website_watch(token, chat_id):
    token, chat_id = ts.resolve_credentials(token, chat_id)
    sent = alerts.run_live_website_watch(token, chat_id)
    count = sent["live_website_watch"]
    print(f"Live website watch complete: {count} message(s) sent" if count
          else "Live website watch complete: all watched sites unchanged")


def _cmd_client_health_scan():
    print("Client health scan: scoring every won lead...")
    results = customer_success.scan_all_clients()
    at_risk = [r for r in results if r["score"] < customer_success.AT_RISK_THRESHOLD]
    print(f"Scored {len(results)} client(s), {len(at_risk)} at risk (score < {customer_success.AT_RISK_THRESHOLD})")
    for r in at_risk:
        print(f"  lead #{r['lead_id']}: {r['score']}/100 — {r['signals']}")
    print("DB stored: True (client_health_scores, client_health_events)")


def _cmd_client_health_check(token, chat_id):
    token, chat_id = ts.resolve_credentials(token, chat_id)
    sent = alerts.run_client_health_check(token, chat_id)
    count = sent["client_health"]
    print(f"Client health alert check complete: {count} message(s) sent" if count
          else "Client health alert check complete: no new at-risk client to report")


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


def _cmd_website_health_check():
    from . import website_health
    results = website_health.check_all_watched_sites()
    for r in results:
        lc = r["latest_check"]
        flag = "ALERT" if r["in_alert"] else "ok"
        ssl_part = f"  SSL: {lc['ssl_days_remaining']}d" if lc["ssl_days_remaining"] is not None else ""
        print(f"[{flag:5s}] {r['label']:40s} {lc['status']:8s} "
              f"code={lc['status_code']}  {lc['response_time_ms']}ms{ssl_part}")
        if lc["error_detail"]:
            print(f"         {lc['error_detail']}")


def _cmd_local_backup_create(reason):
    from . import backup_manager
    result = backup_manager.create_local_backup(reason)
    print(f"Status: {result['status']}" + (f"  -> {result['generation']}" if result.get("generation") else ""))
    print(f"  tests passed: {result['tests']['passed']}   build passed: {result['build']['passed']}")
    print(f"  db readable: {result['database'].get('readable')}   app launches: {result['app_launch'].get('launches')}")
    print(f"  security gate clean: {result['security_gate']['clean']}")
    print(f"  tarball: {result['tarball']['filename']}  ({result['tarball']['size_bytes']} bytes)  sha256={result['tarball']['sha256'][:16]}...")


def _cmd_local_backup_list():
    from . import backup_manager
    result = backup_manager.list_local_generations()
    for g in result["generations"]:
        if g.get("status") == "empty":
            print(f"{g['generation']}: empty")
        else:
            print(f"{g['generation']}: {g['status']}  {g['timestamp']}  reason={g['reason']!r}")
    if result["unverified_snapshots"]:
        print(f"Unverified snapshots: {len(result['unverified_snapshots'])}")
        for u in result["unverified_snapshots"]:
            print(f"  {u['timestamp']}  reason={u['reason']!r}")


def _cmd_local_backup_verify(gen):
    from . import backup_manager
    result = backup_manager.verify_generation(gen)
    print(json.dumps(result, indent=2))


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


def _cmd_sentinel_forecast(metric: str, threshold: float):
    result = sentinel.forecast(metric, threshold=threshold)
    print(f"Metric: {result['metric']}   Current: {result['current']}")
    if result["days_to_threshold"] is None:
        print(f"  No projection: {result['reason']}")
    else:
        print(f"  Trend: {result['slope_per_day']}/day   Threshold: {result['threshold']}")
        print(f"  Days to threshold: {result['days_to_threshold']}  ({result['reason']})")


def _cmd_payment_certify(product: str, provider: str, environment: str, signals_json: str):
    signals = json.loads(signals_json) if signals_json else {}
    result = payment_certification.certify(product, provider, environment, signals)
    print(f"PAYMENT CERTIFICATION -- {result['product']} / {result['provider']} / {result['environment']}")
    print(f"  Security: {result['security_score']}/100   Reliability: {result['reliability_score']}/100   Overall: {result['overall_score']}/100")
    print(f"  RESULT: {result['result']}")
    if result["blocking_failures"]:
        print("  Blocking failures:")
        for f in result["blocking_failures"]:
            print(f"    - {f}")


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


def _cmd_website_audit(url, telegram_token, telegram_chat_id, sheets_credentials, sheets_id,
                        amount=None, razorpay_key_id=None, razorpay_key_secret=None,
                        customer_name=None, customer_contact=None):
    print(f"WEB-001: Auditing {url} ...")
    result = website_audit.run_website_audit(url, telegram_token, telegram_chat_id, sheets_credentials, sheets_id,
                                              payment_amount_inr=amount, razorpay_key_id=razorpay_key_id,
                                              razorpay_key_secret=razorpay_key_secret,
                                              customer_name=customer_name, customer_contact=customer_contact)
    print()
    print(result["report_text"])
    print()
    print(f"Findings: {result['findings_count']} across {result['pages_checked']} pages/resources checked")
    print(f"Telegram sent: {result['telegram_sent']}" + (f" (error: {result.get('telegram_error')})" if result.get("telegram_error") else ""))
    print(f"Sheets synced: {result['sheets_synced']}" + (f" ({result.get('sheets_error')})" if result.get("sheets_error") else ""))
    print(f"DB stored: True (audits #{result['audit_id']}, audit_findings)")
    if result.get("payment_link"):
        print(f"Payment link: {result['payment_link']}")
    elif result.get("payment_error"):
        print(f"Payment link NOT created (error: {result['payment_error']})")


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


def _cmd_create_payment_link(key_id, key_secret, amount, description, customer_name, customer_contact, reference_id):
    result = payments.create_payment_link(key_id, key_secret, amount, description,
                                           customer_name=customer_name, customer_contact=customer_contact,
                                           reference_id=reference_id)
    with db.get_conn() as conn:
        db.insert_payment_link(conn, result["id"], result["short_url"], result["amount_inr"], description,
                                customer_name=customer_name, customer_contact=customer_contact,
                                reference_id=reference_id, status=result["status"])
    print(f"Payment link created: {result['short_url']}")
    print(f"  id: {result['id']}  amount: Rs.{result['amount_inr']}  status: {result['status']}")
    print("Stored in DB (payment_links). Send the URL above to the customer.")


def _cmd_check_payment(key_id, key_secret, link_id):
    result = payments.get_payment_link_status(key_id, key_secret, link_id)
    with db.get_conn() as conn:
        db.update_payment_link_status(conn, result["id"], result["status"])
    print(f"Payment link {result['id']}: status={result['status']} "
          f"paid=Rs.{result['amount_paid_inr']}/Rs.{result['amount_inr']}")


def _cmd_payment_links(status, limit):
    with db.get_conn() as conn:
        rows = db.list_payment_links(conn, status=status, limit=limit)
    if not rows:
        print("No payment links created yet.")
        return
    for r in rows:
        print(f"#{r['id']} [{r['status']}] Rs.{r['amount_inr']} · {r['description']} · "
              f"{r['customer_name'] or '(no name)'} · {r['short_url']} · {r['created_at']}")


def _cmd_website_review(url, business_id, telegram_token, telegram_chat_id):
    print(f"Chrome Developer Bot: reviewing {url} ...")
    result = chrome_developer.review_website(url, business_id=business_id,
                                              telegram_token=telegram_token, telegram_chat_id=telegram_chat_id)
    print()
    print(result["report_text"])
    print()
    print(f"Browser-driven checks available: {result['browser_audit_available']}")
    print(f"Telegram sent: {result['telegram_sent']}" + (f" (error: {result.get('telegram_error')})" if result.get("telegram_error") else ""))
    print(f"DB stored: True (website_reviews #{result['review_id']})")


def _cmd_stripe_checkout(secret_key, amount, currency, description, success_url, cancel_url):
    result = payment_gateway_manager.create_stripe_checkout_session(secret_key, amount, currency, description,
                                                                      success_url, cancel_url)
    print(f"Stripe Checkout session created: {result['checkout_url']}")
    print(f"  session_id: {result['session_id']}")


def _cmd_upi_link(vpa, payee_name, amount, note):
    link = payment_gateway_manager.generate_upi_link(vpa, payee_name, amount, note=note or "")
    print(f"UPI link: {link}")


def _cmd_gateway_status(razorpay_key_id, razorpay_key_secret, stripe_secret_key, upi_vpa, payu_merchant_key, payu_merchant_salt):
    status = payment_gateway_manager.gateway_status(razorpay_key_id=razorpay_key_id, razorpay_key_secret=razorpay_key_secret,
                                                      stripe_secret_key=stripe_secret_key, upi_vpa=upi_vpa,
                                                      payu_merchant_key=payu_merchant_key, payu_merchant_salt=payu_merchant_salt)
    for gateway, s in status.items():
        print(f"{gateway}: configured={s['configured']} valid={s['valid']}")


def _cmd_create_subscription_plan(razorpay_key_id, razorpay_key_secret, amount, plan_name, interval, period):
    result = payment_gateway_manager.create_razorpay_subscription_plan(razorpay_key_id, razorpay_key_secret, amount,
                                                                         plan_name, interval=interval, period=period)
    print(f"Subscription plan created: {result['plan_id']}")


def _cmd_create_subscription(razorpay_key_id, razorpay_key_secret, plan_id, total_count):
    result = payment_gateway_manager.create_razorpay_subscription(razorpay_key_id, razorpay_key_secret, plan_id,
                                                                    total_count=total_count)
    print(f"Subscription created: {result['subscription_id']}")
    if result.get("short_url"):
        print(f"  Customer signup link: {result['short_url']}")


def _cmd_prompt_render(target, role, task, output_format):
    prompt = prompt_engine.render_prompt(target, role, task, output_format=output_format)
    print(prompt)


def _cmd_prompt_lint(agent_id):
    with db.get_conn() as conn:
        agent = db.get_agent(conn, agent_id)
    if not agent:
        print(f"no such agent: {agent_id}")
        return
    issues = prompt_engine.lint_role_prompt(agent["role_prompt"])
    if not issues:
        print(f"{agent_id}: no structural issues found")
    else:
        print(f"{agent_id}: {len(issues)} issue(s)")
        for i in issues:
            print(f"  - {i}")


def _cmd_worker_enqueue(kind, payload_json, priority):
    payload = json.loads(payload_json) if payload_json else {}
    qid = worker_pool.enqueue_task(kind, payload, priority=priority)
    print(f"Enqueued work #{qid} [{kind}]")


def _cmd_worker_drain(max_workers, telegram_token, telegram_chat_id):
    result = worker_pool.drain_queue(max_workers=max_workers, telegram_token=telegram_token, telegram_chat_id=telegram_chat_id)
    print(f"Dispatched: {result['dispatched']}  Succeeded: {result['succeeded']}  Failed: {result['failed']}")
    if result.get("failures"):
        for f in result["failures"]:
            print(f"  FAILED #{f['id']} [{f['kind']}]: {f['error']}")
    lb = result["load_balancer"]
    print(f"Load balancer: queue_depth={lb['queue_depth']} scaled_up={lb['scaled_up']} overflowing={lb['overflowing']}")


def _cmd_worker_daemon(interval_seconds, telegram_token, telegram_chat_id):
    worker_pool.run_worker_daemon(interval_seconds, telegram_token=telegram_token, telegram_chat_id=telegram_chat_id)


def _cmd_worker_status():
    worker_pool.ensure_workers_registered()
    with db.get_conn() as conn:
        workers = db.list_workers(conn)
        lb = load_manager.load_balancer_status(conn)
        queue = db.list_work_queue(conn, limit=20)
    print(f"Load Balancer: queue_depth={lb['queue_depth']} threshold={lb['scale_threshold']} "
          f"max={lb['max_queue_size']} scaled_up={lb['scaled_up']} overflowing={lb['overflowing']}")
    print()
    print("Workers:")
    for w in workers:
        print(f"  {w['name']:16} [{w['status']:5}] completed={w['tasks_completed']} failed={w['tasks_failed']} last_active={w['last_active_at'] or '-'}")
    print()
    print("Recent queue:")
    for q in queue:
        print(f"  #{q['id']} [{q['status']:8}] {q['kind']} (priority={q['priority']}) {q['created_at']}")


def _cmd_pdf_process(operation, inputs, output, password, degrees, pages_str):
    if not inputs:
        print("--pdf-process requires at least one --pdf-input")
        return
    page_numbers = [int(p) for p in pages_str.split(",")] if pages_str else None
    try:
        if operation == "merge":
            result = pdf_studio.merge_pdfs(inputs, output)
        elif operation == "split":
            split_result = pdf_studio.split_pdf(inputs[0], output)
            zip_path = str(Path(output) / "split_pages.zip")
            result = {**split_result, **pdf_studio.zip_dir(output, zip_path)}
        elif operation == "compress":
            result = pdf_studio.compress_pdf(inputs[0], output)
        elif operation == "images-to-pdf":
            result = pdf_studio.images_to_pdf(inputs, output)
        elif operation == "rotate":
            if degrees is None:
                print("--pdf-operation rotate requires --pdf-degrees")
                return
            result = pdf_studio.rotate_pdf(inputs[0], output, degrees, page_numbers=page_numbers)
        elif operation == "extract":
            if not page_numbers:
                print("--pdf-operation extract requires --pdf-pages, e.g. --pdf-pages 1,3,5")
                return
            result = pdf_studio.extract_pages(inputs[0], output, page_numbers)
        elif operation == "protect":
            if not password:
                print("--pdf-operation protect requires --pdf-password")
                return
            result = pdf_studio.password_protect(inputs[0], output, password)
        elif operation == "unprotect":
            if not password:
                print("--pdf-operation unprotect requires --pdf-password")
                return
            result = pdf_studio.remove_password(inputs[0], output, password)
        else:
            print(f"unknown --pdf-operation: {operation}")
            return
    except pdf_studio.PdfStudioError as e:
        print(f"PDF Studio error: {e}")
        return
    print(f"{operation}: {result}")


def _cmd_incident_create(incident_type, description, telegram_token, telegram_chat_id):
    result = incident_manager.create_incident(incident_type, description,
                                               telegram_token=telegram_token, telegram_chat_id=telegram_chat_id)
    print(f"{result['incident_number']} created — type={incident_type} severity={result['severity']} "
          f"owner={result['owner']}{' (ESCALATED)' if result['escalated'] else ''}")
    print(f"  support: {', '.join(result['support_team'])}")
    print(f"  reason: {result['reason']}")


def _cmd_incident_transition(incident_number, status, note):
    result = incident_manager.transition(incident_number, status, note=note or "")
    print(f"{incident_number}: {result['status']}")


def _cmd_incident_resolve(incident_number, root_cause, fix):
    if not (root_cause and fix):
        print("--incident-resolve requires --root-cause and --fix")
        return
    result = incident_manager.resolve(incident_number, root_cause, fix)
    print(f"{incident_number}: RESOLVED (root_cause={root_cause})")


def _cmd_incident_close(incident_number):
    result = incident_manager.close(incident_number)
    print(f"{incident_number}: CLOSED")
    if result.get("postmortem_error"):
        print(f"  postmortem generation failed: {result['postmortem_error']}")
    else:
        print(f"  postmortem: {config.POSTMORTEMS_DIR / (incident_number + '_postmortem.md')}")


def _cmd_incident_list(status):
    with db.get_conn() as conn:
        rows = db.list_incidents(conn, status=status, limit=50)
    if not rows:
        print("No incidents.")
        return
    for r in rows:
        print(f"{r['incident_number']} [{r['status']}] {r['severity']} {r['incident_type']} owner={r['owner']} {r['created_at']}")


def _cmd_incident_sweep(website_urls, telegram_token, telegram_chat_id):
    urls = website_urls.split(",") if website_urls else None
    result = incident_scheduler.run_detection_sweep(website_urls=urls, telegram_token=telegram_token, telegram_chat_id=telegram_chat_id)
    print(f"Detection sweep: {result['count']} incident(s) created")
    for inc in result["incidents_created"]:
        print(f"  {inc['incident_number']} — {inc['incident_type']} ({inc['severity']})")


def _cmd_pricing_check(email, product):
    try:
        result = pricing.check_access(email, product)
    except pricing.PricingError as e:
        print(json.dumps({"error": str(e)}))
        return
    print(json.dumps(result, default=str))


def _cmd_pricing_record_usage(email, product):
    try:
        count = pricing.record_usage(email, product)
    except pricing.PricingError as e:
        print(json.dumps({"error": str(e)}))
        return
    print(json.dumps({"email": email, "product": product, "use_count": count}))


def _cmd_lead_ingest(business_id, name, email, source, contact, notes, telegram_token, telegram_chat_id):
    result = sales.ingest_lead(business_id, name, email, source, contact=contact, notes=notes,
                                telegram_token=telegram_token, telegram_chat_id=telegram_chat_id)
    print(json.dumps(result, default=str))


def _cmd_lead_score(lead_id):
    print(json.dumps(sales.score_lead(lead_id), default=str))


def _cmd_lead_outreach(lead_id):
    print(json.dumps(sales.draft_outreach(lead_id), default=str))


def _cmd_lead_proposal(lead_id, deal_context):
    print(json.dumps(sales.draft_proposal(lead_id, deal_context or ""), default=str))


def _cmd_lead_list(status, owner):
    with db.get_conn() as conn:
        leads = db.list_leads(conn, status=status, owner=owner)
    print(json.dumps(leads, default=str))


def _cmd_marketing_generate(business_id, content_type, target, brief, count):
    results = marketing.generate_content(business_id, content_type, target, brief, count=count)
    print(json.dumps(results, default=str))


def _cmd_marketing_send_to_sales(content_id, lead_id):
    print(json.dumps(marketing.send_to_sales(content_id, lead_id=lead_id), default=str))


def _cmd_content_list(content_type, status):
    with db.get_conn() as conn:
        items = db.list_content_queue(conn, content_type=content_type, status=status)
    print(json.dumps(items, default=str))


def _cmd_team_add_worker(business_id, name, role, contact):
    worker_id = team_register.add_worker(business_id, name, role=role, contact=contact)
    print(json.dumps({"worker_id": worker_id, "name": name}))


def _cmd_team_list_workers(business_id, status):
    print(json.dumps(team_register.list_workers(business_id=business_id, status=status), default=str))


def _cmd_team_log_day(worker_id, work_date, present, hours, work_assigned, work_done, notes):
    entry = team_register.log_day(worker_id, work_date, present=present, hours_worked=hours,
                                    work_assigned=work_assigned, work_done=work_done, notes=notes)
    print(json.dumps(entry, default=str))


def _cmd_team_day_summary(work_date, business_id):
    print(json.dumps(team_register.daily_summary(work_date, business_id=business_id), default=str))


def _cmd_team_worker_summary(worker_id, date_from, date_to):
    print(json.dumps(team_register.worker_summary(worker_id, date_from=date_from, date_to=date_to), default=str))


def _cmd_team_worker_history(worker_id, date_from, date_to):
    print(json.dumps(team_register.worker_history(worker_id, date_from=date_from, date_to=date_to), default=str))


def _cmd_skill_test_all():
    for r in skill_test.run_all():
        print(json.dumps(r, default=str))


def _cmd_skill_test_one(agent_id):
    print(json.dumps(skill_test.grade_agent(agent_id), default=str))


def _cmd_skill_review_list():
    print(json.dumps(skill_test.latest_reviews(), default=str))


def _cmd_dhansetu_ingest_sheet(business_id, credentials_path, spreadsheet_id, sheet_name):
    ids = dhansetu_ai.ingest_course_titles_from_sheet(business_id, credentials_path, spreadsheet_id, sheet_name or "Courses")
    print(json.dumps({"course_ids": ids, "count": len(ids)}))


def _cmd_dhansetu_draft_course(course_id):
    print(json.dumps(dhansetu_ai.draft_course(course_id), default=str))


def _cmd_dhansetu_write_prompt(course_id, brief):
    print(json.dumps(dhansetu_ai.write_visual_prompt(course_id, brief=brief), default=str))


def _cmd_dhansetu_write_reel(course_id, brief):
    print(json.dumps(dhansetu_ai.write_reel_script(course_id, brief=brief), default=str))


def _cmd_dhansetu_schedule_post(content_id, platform):
    print(json.dumps(dhansetu_ai.schedule_post(content_id, platform=platform or "instagram"), default=str))


def _cmd_dhansetu_list_courses(business_id, status):
    with db.get_conn() as conn:
        print(json.dumps(db.list_courses(conn, business_id=business_id, status=status), default=str))


def _cmd_dhansetu_ready_to_post(platform):
    print(json.dumps(dhansetu_ai.list_ready_to_post(platform=platform or "instagram"), default=str))


def _cmd_pa_refine(message, business_id):
    print(json.dumps(pa_angella.refine_prompt(message, business_id=business_id), default=str))


def _cmd_pa_send_to_ceo(message, business_id):
    print(json.dumps(pa_angella.refine_and_send_to_ceo(message, business_id=business_id), default=str))


def _cmd_pa_voice(message, business_id, gender):
    print(json.dumps(pa_angella.refine_and_speak(message, business_id=business_id, gender=gender or "female"), default=str))


def _cmd_dhansetu_add_link(business_id, title, url, sort_order):
    with db.get_conn() as conn:
        link_id = db.insert_link(conn, business_id, title, url, sort_order or 0)
    print(json.dumps({"link_id": link_id, "title": title, "url": url}))


def _cmd_dhansetu_list_links(business_id):
    with db.get_conn() as conn:
        print(json.dumps(db.list_links(conn, business_id=business_id, active_only=False), default=str))


def _cmd_discovery_start(args):
    fields = {key: getattr(args, f"discovery_{key}") for key, _label, _req in onboarding.INTAKE_FIELDS}
    try:
        discovery_id = onboarding.start_discovery(fields)
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        return
    print(json.dumps({"discovery_id": discovery_id}))


def _cmd_discovery_analyze(discovery_id):
    print(json.dumps(onboarding.analyze_discovery(discovery_id), default=str))


def _cmd_discovery_list(status):
    with db.get_conn() as conn:
        print(json.dumps(db.list_business_discoveries(conn, status=status), default=str))


def _cmd_subscribe(email, product, gateway, razorpay_key_id, razorpay_key_secret, payu_merchant_key,
                    payu_merchant_salt, success_url, failure_url):
    razorpay_key_id = razorpay_key_id or os.environ.get("RAZORPAY_KEY_ID")
    razorpay_key_secret = razorpay_key_secret or os.environ.get("RAZORPAY_KEY_SECRET")
    payu_merchant_key = payu_merchant_key or os.environ.get("PAYU_MERCHANT_KEY")
    payu_merchant_salt = payu_merchant_salt or os.environ.get("PAYU_MERCHANT_SALT")
    kwargs = {}
    if gateway == "razorpay":
        if not (razorpay_key_id and razorpay_key_secret):
            print("--subscribe --gateway razorpay requires --razorpay-key-id and --razorpay-key-secret")
            return
        kwargs = {"razorpay_key_id": razorpay_key_id, "razorpay_key_secret": razorpay_key_secret}
    elif gateway == "payu":
        if not (payu_merchant_key and payu_merchant_salt and success_url and failure_url):
            print("--subscribe --gateway payu requires --payu-merchant-key, --payu-merchant-salt, --success-url, --failure-url")
            return
        kwargs = {"payu_merchant_key": payu_merchant_key, "payu_merchant_salt": payu_merchant_salt,
                  "success_url": success_url, "failure_url": failure_url}
    else:
        print("--gateway must be 'razorpay' or 'payu'")
        return

    try:
        result = pricing.create_subscription_payment(email, product, gateway, **kwargs)
    except (pricing.PricingError, payment_gateway_manager.PaymentGatewayError) as e:
        # Real gap found live-testing server-side credentials: this used to
        # let a gateway failure (e.g. a bad key -> Razorpay 401) crash
        # uncaught, which dumped a full Python stack trace -- file paths
        # included -- straight into the API route's JSON error response.
        print(json.dumps({"error": str(e)}))
        return
    print(json.dumps(result, default=str))


def _cmd_create_razorpay_order(razorpay_key_id, razorpay_key_secret, amount_inr, receipt, description, product=None):
    razorpay_key_id = razorpay_key_id or os.environ.get("RAZORPAY_KEY_ID")
    razorpay_key_secret = razorpay_key_secret or os.environ.get("RAZORPAY_KEY_SECRET")
    if not (razorpay_key_id and razorpay_key_secret):
        print(json.dumps({"error": "--create-razorpay-order requires --razorpay-key-id and --razorpay-key-secret"}))
        return
    if not (product and receipt):
        print(json.dumps({"error": "--create-razorpay-order requires --product and --receipt"}))
        return
    # Real gap found and closed same session: this Orders/Checkout.js path
    # is the actual live checkout customers use (default gateway as of
    # tonight), but it takes a raw amount/receipt with no idea a product
    # like blackboxops_os_starter has a hard 300-customer cap -- that cap
    # lived only in pricing.py's OLDER Payment-Links path, which nothing
    # calls anymore on the real pricing page. Checked here too, same
    # source of truth (pricing.PRODUCT_PRICING + db.count_active_subscriptions),
    # not a second, drifting copy of the limit.
    if product:
        try:
            product_pricing = pricing.resolve_order_product(product)
        except pricing.PricingError as e:
            print(json.dumps({"error": str(e)}))
            return
        amount_inr = product_pricing["price_inr"]
        max_customers = product_pricing.get("max_customers")
        if max_customers is not None:
            with db.get_conn() as conn:
                already_sold = db.count_paid_transactions_for_product(conn, product)
            if already_sold >= max_customers:
                print(json.dumps({
                    "error": f"'{product_pricing['label']}' is sold out -- all {max_customers} spots "
                             f"at this price are taken ({already_sold} confirmed).",
                    "sold_out": True,
                }))
                return
    try:
        order = payment_gateway_manager.create_razorpay_order(razorpay_key_id, razorpay_key_secret, amount_inr, receipt)
    except payment_gateway_manager.PaymentGatewayError as e:
        print(json.dumps({"error": str(e)}))
        return
    with db.get_conn() as conn:
        db.insert_payment_transaction(
            # description = the exact product id when known (never the
            # receipt string) -- count_paid_transactions_for_product's
            # exact match depends on this being clean, not a timestamped
            # receipt like "blackboxops_os_starter_1735689600000".
            conn, gateway="razorpay_order", gateway_ref=order["order_id"], amount=amount_inr,
            currency="INR", description=product or description or receipt, status="created",
            customer_email=None,  # Passed from frontend checkout, not CLI
        )
    print(json.dumps(order, default=str))


def _cmd_process_razorpay_webhook(webhook_secret, raw_body, signature):
    if not (webhook_secret and raw_body and signature):
        print(json.dumps({"error": "--process-razorpay-webhook requires --webhook-secret, --raw-body, --razorpay-signature"}))
        return
    body_bytes = raw_body.encode()
    if not payment_gateway_manager.verify_razorpay_webhook_signature(body_bytes, signature, webhook_secret):
        # Fail loud and specific -- a webhook with a bad signature is
        # either a real attacker or a misconfigured secret, never
        # something to silently accept as if it were verified.
        print(json.dumps({"error": "webhook signature verification failed -- not processed", "verified": False}))
        return

    try:
        event = json.loads(raw_body)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"signature verified but body is not valid JSON: {e}", "verified": True}))
        return

    event_type = event.get("event", "")
    payment_entity = event.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment_entity.get("order_id")
    payment_id = payment_entity.get("id")

    # Razorpay retries webhooks that don't get a 200 -- idempotent by
    # design (same event can arrive more than once), so this only ever
    # updates status, never inserts a duplicate row. A webhook for an
    # order this system never created (e.g. a stray/test event) is
    # reported, not silently dropped, so it doesn't look like it worked.
    STATUS_BY_EVENT = {
        "payment.captured": "paid", "order.paid": "paid",
        "payment.failed": "failed",
    }
    result = {"verified": True, "event": event_type, "order_id": order_id, "payment_id": payment_id}
    if not order_id:
        result["error"] = "webhook verified but payload had no order_id to match against"
        print(json.dumps(result))
        return
    new_status = STATUS_BY_EVENT.get(event_type)
    if new_status is None:
        result["note"] = f"event type {event_type!r} verified but not one this handler acts on -- ignored, not an error"
        print(json.dumps(result))
        return

    with db.get_conn() as conn:
        existing = db.get_payment_transaction(conn, order_id)
        if existing is None:
            result["error"] = f"no local payment_transactions row for order_id {order_id!r} -- nothing to update"
            print(json.dumps(result))
            return
        db.update_payment_transaction_status(conn, order_id, new_status)
    result["updated_status"] = new_status
    print(json.dumps(result))


def _cmd_verify_razorpay_payment(razorpay_key_secret, order_id, payment_id, signature):
    razorpay_key_secret = razorpay_key_secret or os.environ.get("RAZORPAY_KEY_SECRET")
    if not (razorpay_key_secret and order_id and payment_id and signature):
        print(json.dumps({"error": "--verify-razorpay-payment requires --razorpay-key-secret, --order-id, --payment-id, --razorpay-signature"}))
        return
    ok = payment_gateway_manager.verify_razorpay_checkout_signature(razorpay_key_secret, order_id, payment_id, signature)
    with db.get_conn() as conn:
        db.update_payment_transaction_status(conn, order_id, "paid" if ok else "failed")
        txn = db.get_payment_transaction(conn, order_id)
    print(json.dumps({"verified": ok, "transaction": txn}, default=str))


def _cmd_initiative_add(title, artifact_url, track="task"):
    result = initiatives.add_initiative(title, artifact_url=artifact_url, track=track)
    label = "Task" if track == "task" else "OS" if track == "os" else "Project"
    print(f"{label} {result['seq']} (#{result['id']}): {title}")


def _cmd_milestone_add(initiative_id, title, done):
    result = initiatives.add_milestone(initiative_id, title, done=done)
    label = "Task" if result["track"] == "task" else "OS" if result["track"] == "os" else "Project"
    print(f"Milestone added to {label} {result['seq']} -- now {result['percent_complete']}% "
          f"({result['milestone_done']}/{result['milestone_total']})")


def _cmd_milestone_done(milestone_id):
    initiatives.mark_milestone(milestone_id, done=True)
    print(f"Milestone #{milestone_id} marked done")


def _cmd_initiative_status(initiative_id, status):
    result = initiatives.set_status(initiative_id, status)
    label = "Task" if result["track"] == "task" else "OS" if result["track"] == "os" else "Project"
    print(f"{label} {result['seq']} status -> {result['status']}")


def _cmd_initiatives_list():
    rows = initiatives.list_all()
    if not rows:
        print("No initiatives tracked yet.")
        return
    for r in rows:
        print(f"Task {r['seq']} (#{r['id']}) [{r['status']}] {r['percent_complete']}% "
              f"({r['milestone_done']}/{r['milestone_total']}) -- {r['title']}")
        for m in r["milestones"]:
            mark = "x" if m["done"] else " "
            print(f"    [{mark}] #{m['id']} {m['title']}")


def _cmd_failure_analysis_add(json_path):
    with open(json_path) as f:
        data = json.load(f)
    required = ("source_type", "title", "severity", "summary", "five_whys",
                "root_cause", "corrective_action", "preventive_action", "lessons_learned")
    missing = [k for k in required if k not in data]
    if missing:
        print(json.dumps({"error": f"missing required field(s): {', '.join(missing)}"}))
        return
    analysis_id = failure_analysis.record_analysis(
        data["source_type"], data.get("source_id"), data["title"], data["severity"],
        data["summary"], data["five_whys"], data["root_cause"], data["corrective_action"],
        data["preventive_action"], data["lessons_learned"], data.get("status", "open"),
    )
    print(f"Failure analysis #{analysis_id} recorded: {data['title']}")


def _cmd_failure_analyses_list(status):
    rows = failure_analysis.list_analyses(status=status)
    if not rows:
        print("No failure analyses recorded yet.")
        return
    for r in rows:
        print(f"#{r['id']} [{r['severity']}] [{r['status']}] {r['title']}")
        print(f"    Root cause: {r['root_cause']}")
        print(f"    Preventive action: {r['preventive_action']}")


def _cmd_peopledesk_add_staff(owner_email, name, role, phone, pay_type, daily_wage, monthly_salary, join_date):
    try:
        staff = peopledesk.add_staff(owner_email, name, role or "", phone or "", pay_type,
                                      daily_wage, monthly_salary, join_date or "")
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        return
    print(json.dumps(staff, default=str))


def _cmd_peopledesk_list_staff(owner_email, status):
    print(json.dumps({"staff": peopledesk.list_staff(owner_email, status=status)}, default=str))


def _cmd_peopledesk_mark_attendance(staff_id, attendance_date, status):
    try:
        peopledesk.mark_attendance(staff_id, attendance_date, status)
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        return
    print(json.dumps({"ok": True}))


def _cmd_peopledesk_payroll(owner_email, date_from, date_to):
    print(json.dumps({"summary": peopledesk.payroll_summary(owner_email, date_from, date_to)}, default=str))


def _cmd_strategy_add(name, symbol, rule_type, params_json):
    try:
        params = json.loads(params_json)
        strategy = trading_engine.create_strategy(name, symbol, rule_type, params)
    except (trading_engine.TradingEngineError, json.JSONDecodeError) as e:
        print(json.dumps({"error": str(e)}))
        return
    print(json.dumps(strategy, default=str))


def _cmd_strategies_list(status):
    print(json.dumps({"strategies": trading_engine.list_strategies(status=status)}, default=str))


def _cmd_strategy_status(strategy_id, status):
    try:
        trading_engine.set_strategy_status(strategy_id, status)
    except trading_engine.TradingEngineError as e:
        print(json.dumps({"error": str(e)}))
        return
    print(json.dumps({"ok": True}))


def _cmd_trading_check():
    print(json.dumps({"results": trading_engine.run_signal_check()}, default=str))


def _cmd_trading_positions(status):
    print(json.dumps({"positions": trading_engine.list_positions(status=status)}, default=str))


def _cmd_trading_journal(limit):
    print(json.dumps({"journal": trading_engine.list_journal(limit=limit)}, default=str))


def _cmd_trading_price(symbol):
    try:
        price = market_data.current_price(symbol)
    except market_data.MarketDataError as e:
        print(json.dumps({"error": str(e)}))
        return
    print(json.dumps({"symbol": symbol, "price": price}))


def _cmd_chat_message(agent_id, message):
    result = routing.run_task(agent_id, message)
    print(json.dumps({"task_id": result["task_id"], "reply": result["output"]}, default=str))


def _cmd_support_bot_ask(message, email, name, business_id, telegram_token, telegram_chat_id):
    result = support_bot.handle_message(
        message, business_id=business_id, email=email, name=name,
        telegram_token=telegram_token, telegram_chat_id=telegram_chat_id,
    )
    print(json.dumps(result, default=str))


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


def _cmd_voice_listen(seconds, owner_passphrase, voice_gender, voice_mute):
    result = voice.listen_and_execute(seconds=seconds, identity_passphrase=owner_passphrase,
                                       speak_response=not voice_mute, gender=voice_gender)
    print(f"Heard ({result['identity']}, {result['language']}): {result['transcript']}")
    print(f"Routed to: {result['intent']['category']}/{result['intent']['action']}")
    if result.get("ceo_status"):
        print(f"CEO review: {result['ceo_status']}")
    print(f"Result: {result['result']}")


def _cmd_voice_loop(window_seconds, owner_passphrase, voice_gender, voice_mute):
    voice.listen_loop(window_seconds=window_seconds, identity_passphrase=owner_passphrase,
                       announce=not voice_mute, gender=voice_gender)


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
    parser.add_argument("--security-alert-check", action="store_true",
                         help="Standalone security-posture alert: Telegram-alerts only when the latest --security-scan score isn't 100, using its own dedup state (unlike --alerts-sweep, never dumps unrelated historical backlog)")
    parser.add_argument("--founder-review", action="store_true",
                         help="Full-picture review across Shakthi OS + every tracked initiative, with a real CEO-agent counter-solution plan -- sent to Telegram, never auto-acted on")
    parser.add_argument("--domain-dns-check", action="store_true",
                         help="Hourly check: alert once dhansetuhub.info stops resolving to loopback (i.e. is pointed somewhere real)")
    parser.add_argument("--watchdog-scan", action="store_true",
                         help="AI Watchdog: behavioral anomaly scan (denied-call spikes, cost spikes, file tamper, unexpected ports, voice probing) -- stores events in DB, prints report")
    parser.add_argument("--watchdog-alert-check", action="store_true",
                         help="Standalone watchdog alert: Telegram-alerts only on warning/critical watchdog_events since last check, using its own dedup state")
    parser.add_argument("--live-website-watch", action="store_true",
                         help="Real 24/7 uptime/SSL/response-time check on watched_websites (blackboxops.co.in, dhansetuhub.in, +2 more), Telegram alert on any DOWN/RECOVERED/SLOW state change")
    parser.add_argument("--sentinel-alert-check", action="store_true",
                         help="Standalone sentinel alert: Telegram-alerts only on the latest --sentinel-check snapshot's real thresholds (disk/CPU/RAM/Ollama/DB/internet), using its own dedup state (unlike --alerts-sweep, never dumps unrelated historical backlog)")
    parser.add_argument("--client-health-scan", action="store_true",
                         help="Score every won lead's client health (product_usage/product_subscriptions signals) into client_health_scores")
    parser.add_argument("--client-health-check", action="store_true",
                         help="Standalone client-health alert: Telegram-alerts only on newly-scored clients below the at-risk threshold, using its own dedup state (unlike --alerts-sweep, never dumps unrelated historical backlog)")

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

    parser.add_argument("--local-backup-create", metavar="REASON", default=None,
                         help="Run real known-good checks (tests/build/db/security) and create a rotated local backup generation (or an UNVERIFIED_SNAPSHOT if checks fail)")
    parser.add_argument("--local-backup-list", action="store_true", help="List real local backup generations (G1/G2/G3) and any unverified snapshots")
    parser.add_argument("--local-backup-verify", metavar="GEN", default=None, help="Real restore drill against a stored generation, e.g. G1")

    parser.add_argument("--sentinel-check", action="store_true", help="Collect and print a real system health snapshot")
    parser.add_argument("--sentinel-forecast", metavar="METRIC", default=None,
                         help="Real linear-trend projection for a system_health column (e.g. disk_percent) from actual stored history")
    parser.add_argument("--forecast-threshold", type=float, default=90.0, help="Threshold value for --sentinel-forecast (default 90.0)")
    parser.add_argument("--sentinel-loop", action="store_true", help="Continuous monitoring (foreground loop, Ctrl+C to stop)")

    parser.add_argument("--website-health-check", action="store_true",
                         help="Run a real check (HTTP + SSL) against every active watched website and print the results")
    parser.add_argument("--payment-certify", metavar="PRODUCT", default=None,
                         help="Real PRODUCTION READY/NOT verdict for a payment integration -- see --certify-provider/--certify-env/--certify-signals")
    parser.add_argument("--certify-provider", default="PayU")
    parser.add_argument("--certify-env", default="production")
    parser.add_argument("--certify-signals", default="{}", help='JSON dict of real checklist signals, e.g. \'{"https_enforced": true}\'')
    parser.add_argument("--ops-scan", action="store_true", help="OPS-001: Sentinel -> CEO -> Telegram live health scan, stored in DB (+ Sheets if credentials given)")
    parser.add_argument("--security-scan", action="store_true", help="OPS-002: live security posture scan -> Telegram, stored in DB (+ Sheets if credentials given)")
    parser.add_argument("--website-audit", metavar="URL", help="WEB-001: live external website audit -> Telegram, stored in DB (+ Sheets if credentials given)")
    parser.add_argument("--correct", metavar="TASK_TYPE", choices=correction_bot.TASK_TYPES,
                         help=f"Correction Bot: review content from --content-file. Task types: {', '.join(correction_bot.TASK_TYPES)}")
    parser.add_argument("--content-file", help="path to the content file to review, used with --correct")
    parser.add_argument("--task-ref", default=None, help="free-text pointer to the source, used with --correct")
    parser.add_argument("--correction-history", nargs="?", const=20, type=int, metavar="N",
                         help="print the last N corrections (default 20)")
    parser.add_argument("--create-payment-link", action="store_true",
                         help="Razorpay: create a payment link (Offer A). Requires --razorpay-key-id, --razorpay-key-secret, --razorpay-amount, --description")
    parser.add_argument("--check-payment", metavar="LINK_ID", help="Razorpay: fetch a payment link's current status")
    parser.add_argument("--payment-links", action="store_true", help="list payment links stored in the DB")
    parser.add_argument("--razorpay-key-id", default=None, help="Razorpay Key ID -- never stored, passed every invocation")
    parser.add_argument("--razorpay-key-secret", default=None, help="Razorpay Key Secret -- never stored, passed every invocation")
    parser.add_argument("--razorpay-amount", type=float, default=None, help="amount in INR, used with --create-payment-link or --website-audit")
    # --description already declared above (bug reports) -- reused here for --create-payment-link's payer-facing text
    parser.add_argument("--customer-name", default=None)
    parser.add_argument("--customer-contact", default=None, help="customer phone number (E.164 or 10-digit Indian)")
    parser.add_argument("--customer-email", default=None, help="customer email address")
    parser.add_argument("--reference-id", default=None, help="e.g. 'web-audit:dhansetuhub.in'")
    parser.add_argument("--status", default=None, help="filter for --payment-links (created|paid|cancelled|expired)")

    parser.add_argument("--website-review", metavar="URL", help="Chrome Developer Bot: real browser-driven website review -> Telegram, stored in DB")
    parser.add_argument("--stripe-checkout", action="store_true", help="Stripe: create a Checkout session. Requires --stripe-secret-key, --razorpay-amount, --description, --success-url, --cancel-url")
    parser.add_argument("--stripe-secret-key", default=None)
    parser.add_argument("--stripe-currency", default="usd")
    parser.add_argument("--success-url", default=None)
    parser.add_argument("--cancel-url", default=None)
    parser.add_argument("--upi-link", action="store_true", help="Generate a UPI deep link. Requires --upi-vpa, --razorpay-amount, --customer-name (payee name)")
    parser.add_argument("--upi-vpa", default=None, help="e.g. founder@okhdfcbank")
    parser.add_argument("--gateway-status", action="store_true", help="Check which payment gateways are configured/valid")
    parser.add_argument("--create-subscription-plan", action="store_true", help="Razorpay Subscriptions: create a plan. Requires --razorpay-key-id/secret, --razorpay-amount, --plan-name")
    parser.add_argument("--create-subscription", action="store_true", help="Razorpay Subscriptions: subscribe a customer to a plan. Requires --razorpay-key-id/secret, --plan-id")
    parser.add_argument("--plan-id", default=None)
    parser.add_argument("--plan-name", default=None)
    parser.add_argument("--sub-interval", type=int, default=1)
    parser.add_argument("--sub-period", default="monthly", choices=["daily", "weekly", "monthly", "yearly"])
    parser.add_argument("--total-count", type=int, default=12, help="number of billing cycles for --create-subscription")
    parser.add_argument("--prompt-render", action="store_true", help="Render a prompt template. Requires --prompt-target, --prompt-role, --prompt-task")
    parser.add_argument("--prompt-target", default="claude", choices=list(prompt_engine.MODEL_PROFILES))
    parser.add_argument("--prompt-role", default=None)
    parser.add_argument("--prompt-task", default=None)
    parser.add_argument("--prompt-output-format", default=None)
    parser.add_argument("--prompt-lint", metavar="AGENT_ID", help="Lint a registered agent's role_prompt for structural issues")

    parser.add_argument("--worker-enqueue", metavar="KIND", help="Enqueue a task. Requires --payload-json (see worker_registry.TASK_KINDS for valid kinds)")
    parser.add_argument("--payload-json", default=None, help='JSON payload for --worker-enqueue, e.g. \'{"url": "https://example.com"}\'')
    parser.add_argument("--queue-priority", type=int, default=5, help="lower = higher priority, used with --worker-enqueue")
    parser.add_argument("--worker-drain", action="store_true", help="Dispatch all queued work in parallel, once, then exit")
    parser.add_argument("--worker-daemon", action="store_true", help="Continuously drain the queue every --interval seconds (Ctrl+C to stop)")
    parser.add_argument("--worker-status", action="store_true", help="Show Worker Status, Load Balancer Status, and the Task Queue")
    parser.add_argument("--max-workers", type=int, default=None, help="cap concurrency for --worker-drain (default: auto, from load_manager)")

    parser.add_argument("--pdf-process", metavar="OPERATION",
                         choices=["merge", "split", "compress", "images-to-pdf", "rotate", "extract", "protect", "unprotect"],
                         help="Dhansetu PDF Studio: run a real PDF operation")
    parser.add_argument("--pdf-input", action="append", default=[], help="input file path; repeat for multiple files (merge, images-to-pdf)")
    parser.add_argument("--pdf-output", default=None, help="output file path (or directory, for split)")
    parser.add_argument("--pdf-password", default=None, help="used with --pdf-process protect/unprotect")
    parser.add_argument("--pdf-degrees", type=int, default=None, help="used with --pdf-process rotate (multiple of 90)")
    parser.add_argument("--pdf-pages", default=None, help='comma-separated 1-indexed page numbers, e.g. "1,3,5" -- used with rotate/extract')

    parser.add_argument("--incident-create", metavar="INCIDENT_TYPE", help="Create an incident. Requires --description (see incident_registry.OWNERSHIP_MATRIX for valid types)")
    parser.add_argument("--incident-transition", metavar="INCIDENT_NUMBER", help="Move an incident to a new state. Requires --to-status")
    parser.add_argument("--to-status", default=None, choices=incident_manager.STATE_ORDER)
    parser.add_argument("--incident-resolve", metavar="INCIDENT_NUMBER", help="Resolve an incident. Requires --root-cause and --fix")
    parser.add_argument("--root-cause", default=None)
    parser.add_argument("--fix", default=None)
    parser.add_argument("--incident-close", metavar="INCIDENT_NUMBER", help="Close a resolved incident and generate its postmortem")
    parser.add_argument("--incident-list", action="store_true", help="List recent incidents")
    parser.add_argument("--incident-sweep", action="store_true", help="Run automatic emergency detection now")
    parser.add_argument("--website-urls", default=None, help="comma-separated URLs for --incident-sweep to check")

    parser.add_argument("--subscribe", action="store_true", help="Create a subscription payment. Requires --email, --product, --gateway")
    parser.add_argument("--create-razorpay-order", action="store_true", help="Create a real fixed-price Razorpay Order for on-page Checkout.js (not a Payment Link). Requires --razorpay-key-id, --razorpay-key-secret, --amount-inr, --receipt. Optional --product enforces that product's PRODUCT_PRICING cap (e.g. first-300)")
    parser.add_argument("--verify-razorpay-payment", action="store_true", help="Verify a Razorpay Checkout.js success callback's signature. Requires --razorpay-key-secret, --order-id, --payment-id, --razorpay-signature")
    parser.add_argument("--process-razorpay-webhook", action="store_true", help="Verify + process a real Razorpay webhook event. Requires --webhook-secret, --raw-body, --razorpay-signature")
    parser.add_argument("--webhook-secret", default=None, help="Razorpay Webhook Secret (set in the Razorpay dashboard) -- distinct from the API Key Secret, never store or log it")
    parser.add_argument("--raw-body", default=None, help="The exact raw request body Razorpay sent, unmodified -- the signature covers these exact bytes")
    parser.add_argument("--amount-inr", type=float, default=None)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--order-id", default=None)
    parser.add_argument("--payment-id", default=None)
    parser.add_argument("--razorpay-signature", default=None)
    parser.add_argument("--pricing-check", action="store_true", help="Check free-tier/subscription access. Requires --email, --product")
    parser.add_argument("--pricing-record-usage", action="store_true", help="Record one use after an allowed pricing check. Requires --email, --product")
    parser.add_argument("--email", default=None)
    parser.add_argument("--product", default=None, choices=list(pricing.PRODUCT_PRICING))
    parser.add_argument("--gateway", default=None, choices=["razorpay", "payu"])
    parser.add_argument("--failure-url", default=None)

    parser.add_argument("--lead-ingest", action="store_true", help="New lead -> auto-route to sales (score, then outreach or founder escalation). Requires --lead-name, --lead-email, --lead-source")
    parser.add_argument("--lead-score", type=int, default=None, metavar="LEAD_ID", help="Re-score an existing lead")
    parser.add_argument("--lead-outreach", type=int, default=None, metavar="LEAD_ID", help="Draft outreach for an existing lead")
    parser.add_argument("--lead-proposal", type=int, default=None, metavar="LEAD_ID", help="Draft a proposal for an existing lead")
    parser.add_argument("--lead-list", action="store_true", help="List leads")
    parser.add_argument("--lead-name", default=None)
    parser.add_argument("--lead-email", default=None)
    parser.add_argument("--lead-contact", default=None)
    parser.add_argument("--lead-source", default=None)
    parser.add_argument("--lead-notes", default=None)
    parser.add_argument("--lead-status", default=None, help="filter for --lead-list")
    parser.add_argument("--lead-owner", default=None, choices=["sales", "founder"], help="filter for --lead-list")
    parser.add_argument("--deal-context", default=None, help="context for --lead-proposal")

    parser.add_argument("--marketing-generate", action="store_true", help="Generate N content variants. Requires --content-type, --marketing-target, --brief")
    parser.add_argument("--marketing-send-to-sales", type=int, default=None, metavar="CONTENT_ID", help="Hand a content_queue item to the Sales agent")
    parser.add_argument("--content-list", action="store_true", help="List content_queue items")
    parser.add_argument("--content-type", default=None, choices=["linkedin_post", "twitter_thread", "landing_copy", "cold_email", "ad_angle"])
    parser.add_argument("--content-status", default=None, help="filter for --content-list")
    parser.add_argument("--marketing-target", default=None, help="audience for --marketing-generate, e.g. 'agency founders'")
    parser.add_argument("--brief", default=None, help="offer/brief for --marketing-generate")
    parser.add_argument("--count", type=int, default=3, help="number of variants for --marketing-generate")
    parser.add_argument("--lead-id", type=int, default=None, help="target lead for --marketing-send-to-sales (optional)")

    parser.add_argument("--team-add-worker", action="store_true", help="Add a team member. Requires --worker-name")
    parser.add_argument("--team-list-workers", action="store_true", help="List team members")
    parser.add_argument("--team-log-day", action="store_true", help="Log one worker's day. Requires --worker-id, --work-date")
    parser.add_argument("--team-day-summary", metavar="YYYY-MM-DD", default=None, help="Who worked on this date")
    parser.add_argument("--team-worker-summary", type=int, default=None, metavar="WORKER_ID", help="Attendance/hours rollup for one worker")
    parser.add_argument("--team-worker-history", type=int, default=None, metavar="WORKER_ID", help="Raw day-by-day log for one worker")
    parser.add_argument("--worker-name", default=None)
    parser.add_argument("--worker-role", default=None)
    parser.add_argument("--worker-contact", default=None)
    parser.add_argument("--worker-id", type=int, default=None, help="target worker for --team-log-day")
    parser.add_argument("--team-status", default=None, choices=["active", "inactive"], help="filter for --team-list-workers")
    parser.add_argument("--work-date", default=None, help="YYYY-MM-DD, for --team-log-day")
    parser.add_argument("--present", dest="present", action="store_true", default=True, help="default for --team-log-day")
    parser.add_argument("--absent", dest="present", action="store_false", help="mark --team-log-day as absent instead")
    parser.add_argument("--hours", type=float, default=None, help="hours worked, for --team-log-day")
    parser.add_argument("--work-assigned", default=None)
    parser.add_argument("--work-done", default=None)
    parser.add_argument("--notes", default=None)
    parser.add_argument("--date-from", default=None, help="YYYY-MM-DD, for --team-worker-summary/--team-worker-history")
    parser.add_argument("--date-to", default=None, help="YYYY-MM-DD, for --team-worker-summary/--team-worker-history")

    parser.add_argument("--skill-test-all", action="store_true", help="Run the real skill test + 100-point review for all 17 agents")
    parser.add_argument("--skill-test", default=None, metavar="AGENT_ID", help="Run the skill test for one agent")
    parser.add_argument("--skill-review-list", action="store_true", help="Show the latest review per agent, weakest first")

    parser.add_argument("--dhansetu-ingest-sheet", action="store_true", help="Read course titles from the founder's Google Sheet. Requires --sheets-credentials, --sheets-id")
    parser.add_argument("--dhansetu-draft-course", type=int, default=None, metavar="COURSE_ID")
    parser.add_argument("--dhansetu-write-prompt", type=int, default=None, metavar="COURSE_ID")
    parser.add_argument("--dhansetu-write-reel", type=int, default=None, metavar="COURSE_ID")
    parser.add_argument("--dhansetu-schedule-post", type=int, default=None, metavar="CONTENT_ID")
    parser.add_argument("--dhansetu-list-courses", action="store_true")
    parser.add_argument("--dhansetu-ready-to-post", action="store_true")
    parser.add_argument("--course-status", default=None, help="filter for --dhansetu-list-courses")
    parser.add_argument("--platform", default="instagram", help="for --dhansetu-schedule-post/--dhansetu-ready-to-post")
    parser.add_argument("--sheet-name", default="Courses", help="tab name for --dhansetu-ingest-sheet")

    parser.add_argument("--pa-refine", default=None, metavar="MESSAGE", help="Turn a raw message into a professional prompt (PA Angella)")
    parser.add_argument("--pa-send-to-ceo", default=None, metavar="MESSAGE", help="Refine via PA Angella, then send straight to ceo.decide()")
    parser.add_argument("--pa-voice", default=None, metavar="MESSAGE", help="Refine via PA Angella, then speak the refined prompt back out loud")
    parser.add_argument("--pa-voice-gender", choices=["male", "female"], default="female", help="Voice for --pa-voice (default: female, matches her persona)")

    parser.add_argument("--dhansetu-add-link", action="store_true", help="Add a link-tree entry. Requires --link-title, --link-url")
    parser.add_argument("--dhansetu-list-links", action="store_true")
    parser.add_argument("--link-title", default=None)
    parser.add_argument("--link-url", default=None)
    parser.add_argument("--link-order", type=int, default=None)

    parser.add_argument("--discovery-start", action="store_true", help="Stage 1 intake. Requires --discovery-business-name, others optional")
    parser.add_argument("--discovery-analyze", type=int, default=None, metavar="DISCOVERY_ID", help="Run the 5-category bottleneck analysis on an intake")
    parser.add_argument("--discovery-list", action="store_true")
    parser.add_argument("--discovery-status", default=None, choices=["intake", "analyzed"], help="filter for --discovery-list")
    for _key, _label, _req in onboarding.INTAKE_FIELDS:
        parser.add_argument(f"--discovery-{_key.replace('_', '-')}", dest=f"discovery_{_key}", default=None, help=_label)

    parser.add_argument("--payu-merchant-key", default=None)
    parser.add_argument("--payu-merchant-salt", default=None)
    parser.add_argument("--interval", type=int, default=60, help="Seconds between --sentinel-loop collections")

    parser.add_argument("--initiative-add", metavar="TITLE", help="Track a new founder-facing task (Task 1, Task 2, ...)")
    parser.add_argument("--initiative-track", default="task", choices=["task", "project", "os"],
                         help="'task' = web-based work (default), 'project' = big cross-platform software dev (Mac/Windows/Linux/iOS/Android)")
    parser.add_argument("--initiative-artifact-url", default=None, metavar="URL")
    parser.add_argument("--milestone-add", type=int, default=None, metavar="INITIATIVE_ID")
    parser.add_argument("--milestone-title", default=None, metavar="TITLE")
    parser.add_argument("--milestone-done-on-add", action="store_true")
    parser.add_argument("--milestone-done", type=int, default=None, metavar="MILESTONE_ID")
    parser.add_argument("--initiative-status", type=int, default=None, metavar="INITIATIVE_ID")
    parser.add_argument("--initiative-set-status", choices=["running", "paused", "done"], default=None)
    parser.add_argument("--initiatives-list", action="store_true")

    parser.add_argument("--failure-analysis-add", metavar="JSON_PATH",
                         help="Record a real 5-Whys failure analysis from a JSON file")
    parser.add_argument("--failure-analyses-list", action="store_true")
    parser.add_argument("--failure-status", default=None, choices=["open", "closed"],
                         help="Filter for --failure-analyses-list")

    parser.add_argument("--chat-message", metavar="MESSAGE", help="Pre-sales chat widget: one message, one reply, clean JSON")
    parser.add_argument("--chat-agent", default="sales", help="Agent id to answer --chat-message (default: sales)")
    parser.add_argument("--support-bot-ask", metavar="MESSAGE", help="Customer-facing support bot: knowledge-base answer, or lead capture if unmatched + --support-email given")
    parser.add_argument("--support-email", default=None)
    parser.add_argument("--support-name", default=None)
    parser.add_argument("--support-business-id", type=int, default=None)

    parser.add_argument("--peopledesk-add-staff", action="store_true")
    parser.add_argument("--peopledesk-list-staff", action="store_true")
    parser.add_argument("--peopledesk-mark-attendance", action="store_true")
    parser.add_argument("--peopledesk-payroll", action="store_true")
    parser.add_argument("--owner-email", default=None, help="PeopleDesk: which small business's data (email is the identity)")
    parser.add_argument("--staff-name", default=None)
    parser.add_argument("--staff-role", default=None)
    parser.add_argument("--staff-phone", default=None)
    parser.add_argument("--staff-pay-type", choices=["daily", "monthly"], default="daily")
    parser.add_argument("--staff-daily-wage", type=float, default=None)
    parser.add_argument("--staff-monthly-salary", type=float, default=None)
    parser.add_argument("--staff-join-date", default=None)
    parser.add_argument("--staff-status", default="active", choices=["active", "inactive"], help="Filter for --peopledesk-list-staff")
    parser.add_argument("--staff-id", type=int, default=None)
    parser.add_argument("--attendance-date", default=None, help="YYYY-MM-DD")
    parser.add_argument("--attendance-status", choices=["present", "absent", "half_day", "leave"], default=None)

    parser.add_argument("--strategy-add", action="store_true", help="Trading OS: create a paper-trading strategy. Requires --strategy-name/--strategy-symbol/--strategy-rule-type/--strategy-params")
    parser.add_argument("--strategy-name", default=None)
    parser.add_argument("--strategy-symbol", default=None, help="e.g. BTCUSDT")
    parser.add_argument("--strategy-rule-type", choices=["sma_crossover", "rsi_threshold"], default=None)
    parser.add_argument("--strategy-params", default=None, help="JSON, e.g. '{\"fast_period\":10,\"slow_period\":30,\"trade_quantity\":0.001}'")
    parser.add_argument("--strategies-list", action="store_true")
    parser.add_argument("--strategy-status", type=int, default=None, metavar="STRATEGY_ID")
    parser.add_argument("--strategy-set-status", choices=["active", "paused"], default=None)
    parser.add_argument("--trading-check", action="store_true", help="Run one real signal-check pass across all active strategies")
    parser.add_argument("--trading-positions", action="store_true")
    parser.add_argument("--position-status", choices=["open", "closed"], default=None, help="Filter for --trading-positions")
    parser.add_argument("--trading-journal", action="store_true")
    parser.add_argument("--trading-price", default=None, metavar="SYMBOL", help="e.g. BTCUSDT")
    parser.add_argument("--journal-limit", type=int, default=100)

    parser.add_argument("--knowledge-add", metavar="TITLE")
    parser.add_argument("--content", default="")
    parser.add_argument("--tags", default="")
    parser.add_argument("--knowledge-category", default="general")
    parser.add_argument("--knowledge-ask", metavar="QUESTION")

    parser.add_argument("--buddy-chat", metavar="MESSAGE")
    parser.add_argument("--buddy-mode", choices=["child", "family", "general"], default="general")
    parser.add_argument("--session-id", default="cli-session")

    parser.add_argument("--voice-listen", action="store_true", help="Record from the mic and route the command")
    parser.add_argument("--voice-loop", action="store_true", help="Continuous wake-word listening (foreground loop, Ctrl+C to stop)")
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument("--window-seconds", type=float, default=4.0, help="Recording window size for --voice-loop")
    parser.add_argument("--owner-passphrase", default=None, help="Manual entry — not stored anywhere")
    parser.add_argument("--voice-history", nargs="?", const=10, type=int, metavar="LIMIT", help="Print recent voice command history")
    parser.add_argument("--voice-gender", choices=["male", "female"], default="male", help="Which spoken voice answers back (Daniel/Samantha)")
    parser.add_argument("--voice-mute", action="store_true", help="Don't speak the response out loud, text only")

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
    if args.security_alert_check:
        return _cmd_security_alert_check(args.telegram_token, args.telegram_chat_id)
    if args.founder_review:
        return _cmd_founder_review(args.telegram_token, args.telegram_chat_id)
    if args.domain_dns_check:
        return _cmd_domain_dns_check(args.telegram_token, args.telegram_chat_id)
    if args.watchdog_scan:
        return _cmd_watchdog_scan()
    if args.watchdog_alert_check:
        return _cmd_watchdog_alert_check(args.telegram_token, args.telegram_chat_id)
    if args.sentinel_alert_check:
        return _cmd_sentinel_alert_check(args.telegram_token, args.telegram_chat_id)
    if args.live_website_watch:
        return _cmd_live_website_watch(args.telegram_token, args.telegram_chat_id)
    if args.client_health_scan:
        return _cmd_client_health_scan()
    if args.client_health_check:
        return _cmd_client_health_check(args.telegram_token, args.telegram_chat_id)
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
    if args.website_health_check:
        return _cmd_website_health_check()
    if args.local_backup_create is not None:
        return _cmd_local_backup_create(args.local_backup_create)
    if args.local_backup_list:
        return _cmd_local_backup_list()
    if args.local_backup_verify is not None:
        return _cmd_local_backup_verify(args.local_backup_verify)
    if args.sentinel_check:
        return _cmd_sentinel_check()
    if args.sentinel_forecast:
        return _cmd_sentinel_forecast(args.sentinel_forecast, args.forecast_threshold)
    if args.payment_certify:
        return _cmd_payment_certify(args.payment_certify, args.certify_provider, args.certify_env, args.certify_signals)
    if args.sentinel_loop:
        return _cmd_sentinel_loop(args.interval, args.telegram_token, args.telegram_chat_id)
    if args.ops_scan:
        return _cmd_ops_scan(args.telegram_token, args.telegram_chat_id, args.sheets_credentials, args.sheets_id)
    if args.security_scan:
        return _cmd_security_scan(args.telegram_token, args.telegram_chat_id, args.sheets_credentials, args.sheets_id)
    if args.website_audit:
        return _cmd_website_audit(args.website_audit, args.telegram_token, args.telegram_chat_id, args.sheets_credentials, args.sheets_id,
                                   amount=args.razorpay_amount, razorpay_key_id=args.razorpay_key_id, razorpay_key_secret=args.razorpay_key_secret,
                                   customer_name=args.customer_name, customer_contact=args.customer_contact)
    if args.correct:
        if not args.content_file:
            print("--correct requires --content-file PATH")
            return
        return _cmd_correct(args.correct, args.task_ref, args.content_file, args.telegram_token,
                             args.telegram_chat_id, args.sheets_credentials, args.sheets_id)
    if args.correction_history is not None:
        return _cmd_correction_history(args.correction_history)
    if args.create_payment_link:
        if not (args.razorpay_key_id and args.razorpay_key_secret and args.razorpay_amount and args.description):
            print("--create-payment-link requires --razorpay-key-id, --razorpay-key-secret, --razorpay-amount, --description")
            return
        return _cmd_create_payment_link(args.razorpay_key_id, args.razorpay_key_secret, args.razorpay_amount,
                                         args.description, args.customer_name, args.customer_contact, args.reference_id)
    if args.check_payment:
        if not (args.razorpay_key_id and args.razorpay_key_secret):
            print("--check-payment requires --razorpay-key-id and --razorpay-key-secret")
            return
        return _cmd_check_payment(args.razorpay_key_id, args.razorpay_key_secret, args.check_payment)
    if args.payment_links:
        return _cmd_payment_links(args.status, 50)
    if args.website_review:
        return _cmd_website_review(args.website_review, args.business, args.telegram_token, args.telegram_chat_id)
    if args.stripe_checkout:
        if not (args.stripe_secret_key and args.razorpay_amount and args.description and args.success_url and args.cancel_url):
            print("--stripe-checkout requires --stripe-secret-key, --razorpay-amount, --description, --success-url, --cancel-url")
            return
        return _cmd_stripe_checkout(args.stripe_secret_key, args.razorpay_amount, args.stripe_currency,
                                     args.description, args.success_url, args.cancel_url)
    if args.upi_link:
        if not (args.upi_vpa and args.razorpay_amount):
            print("--upi-link requires --upi-vpa and --razorpay-amount")
            return
        return _cmd_upi_link(args.upi_vpa, args.customer_name or "Shakthi", args.razorpay_amount, args.note)
    if args.gateway_status:
        return _cmd_gateway_status(args.razorpay_key_id, args.razorpay_key_secret, args.stripe_secret_key, args.upi_vpa,
                                    args.payu_merchant_key, args.payu_merchant_salt)
    if args.create_subscription_plan:
        if not (args.razorpay_key_id and args.razorpay_key_secret and args.razorpay_amount and args.plan_name):
            print("--create-subscription-plan requires --razorpay-key-id, --razorpay-key-secret, --razorpay-amount, --plan-name")
            return
        return _cmd_create_subscription_plan(args.razorpay_key_id, args.razorpay_key_secret, args.razorpay_amount,
                                              args.plan_name, args.sub_interval, args.sub_period)
    if args.create_subscription:
        if not (args.razorpay_key_id and args.razorpay_key_secret and args.plan_id):
            print("--create-subscription requires --razorpay-key-id, --razorpay-key-secret, --plan-id")
            return
        return _cmd_create_subscription(args.razorpay_key_id, args.razorpay_key_secret, args.plan_id, args.total_count)
    if args.prompt_render:
        if not (args.prompt_role and args.prompt_task):
            print("--prompt-render requires --prompt-role and --prompt-task")
            return
        return _cmd_prompt_render(args.prompt_target, args.prompt_role, args.prompt_task, args.prompt_output_format)
    if args.prompt_lint:
        return _cmd_prompt_lint(args.prompt_lint)
    if args.worker_enqueue:
        return _cmd_worker_enqueue(args.worker_enqueue, args.payload_json, args.queue_priority)
    if args.worker_drain:
        return _cmd_worker_drain(args.max_workers, args.telegram_token, args.telegram_chat_id)
    if args.worker_daemon:
        return _cmd_worker_daemon(args.interval, args.telegram_token, args.telegram_chat_id)
    if args.worker_status:
        return _cmd_worker_status()
    if args.pdf_process:
        if not args.pdf_output:
            print("--pdf-process requires --pdf-output")
            return
        return _cmd_pdf_process(args.pdf_process, args.pdf_input, args.pdf_output, args.pdf_password,
                                 args.pdf_degrees, args.pdf_pages)
    if args.incident_create:
        if not args.description:
            print("--incident-create requires --description")
            return
        return _cmd_incident_create(args.incident_create, args.description, args.telegram_token, args.telegram_chat_id)
    if args.incident_transition:
        if not args.to_status:
            print("--incident-transition requires --to-status")
            return
        return _cmd_incident_transition(args.incident_transition, args.to_status, args.note)
    if args.incident_resolve:
        return _cmd_incident_resolve(args.incident_resolve, args.root_cause, args.fix)
    if args.incident_close:
        return _cmd_incident_close(args.incident_close)
    if args.incident_list:
        return _cmd_incident_list(args.status)
    if args.incident_sweep:
        return _cmd_incident_sweep(args.website_urls, args.telegram_token, args.telegram_chat_id)
    if args.subscribe:
        if not (args.email and args.product and args.gateway):
            print("--subscribe requires --email, --product, --gateway")
            return
        return _cmd_subscribe(args.email, args.product, args.gateway, args.razorpay_key_id, args.razorpay_key_secret,
                               args.payu_merchant_key, args.payu_merchant_salt, args.success_url, args.failure_url)
    if args.create_razorpay_order:
        return _cmd_create_razorpay_order(args.razorpay_key_id, args.razorpay_key_secret, args.amount_inr, args.receipt, None, product=args.product)
    if args.verify_razorpay_payment:
        return _cmd_verify_razorpay_payment(args.razorpay_key_secret, args.order_id, args.payment_id, args.razorpay_signature)
    if args.process_razorpay_webhook:
        return _cmd_process_razorpay_webhook(args.webhook_secret, args.raw_body, args.razorpay_signature)
    if args.pricing_check:
        if not (args.email and args.product):
            print(json.dumps({"error": "--pricing-check requires --email and --product"}))
            return
        return _cmd_pricing_check(args.email, args.product)
    if args.pricing_record_usage:
        if not (args.email and args.product):
            print(json.dumps({"error": "--pricing-record-usage requires --email and --product"}))
            return
        return _cmd_pricing_record_usage(args.email, args.product)
    if args.lead_ingest:
        if not (args.lead_name and args.lead_email and args.lead_source):
            print(json.dumps({"error": "--lead-ingest requires --lead-name, --lead-email, --lead-source"}))
            return
        return _cmd_lead_ingest(args.business, args.lead_name, args.lead_email, args.lead_source,
                                 args.lead_contact, args.lead_notes, args.telegram_token, args.telegram_chat_id)
    if args.lead_score is not None:
        return _cmd_lead_score(args.lead_score)
    if args.lead_outreach is not None:
        return _cmd_lead_outreach(args.lead_outreach)
    if args.lead_proposal is not None:
        return _cmd_lead_proposal(args.lead_proposal, args.deal_context)
    if args.lead_list:
        return _cmd_lead_list(args.lead_status, args.lead_owner)
    if args.marketing_generate:
        if not (args.content_type and args.marketing_target and args.brief):
            print(json.dumps({"error": "--marketing-generate requires --content-type, --marketing-target, --brief"}))
            return
        return _cmd_marketing_generate(args.business, args.content_type, args.marketing_target, args.brief, args.count)
    if args.marketing_send_to_sales is not None:
        return _cmd_marketing_send_to_sales(args.marketing_send_to_sales, args.lead_id)
    if args.content_list:
        return _cmd_content_list(args.content_type, args.content_status)
    if args.team_add_worker:
        if not args.worker_name:
            print(json.dumps({"error": "--team-add-worker requires --worker-name"}))
            return
        return _cmd_team_add_worker(args.business, args.worker_name, args.worker_role, args.worker_contact)
    if args.team_list_workers:
        return _cmd_team_list_workers(args.business, args.team_status)
    if args.team_log_day:
        if not (args.worker_id and args.work_date):
            print(json.dumps({"error": "--team-log-day requires --worker-id and --work-date"}))
            return
        return _cmd_team_log_day(args.worker_id, args.work_date, args.present, args.hours,
                                   args.work_assigned, args.work_done, args.notes)
    if args.team_day_summary:
        return _cmd_team_day_summary(args.team_day_summary, args.business)
    if args.team_worker_summary is not None:
        return _cmd_team_worker_summary(args.team_worker_summary, args.date_from, args.date_to)
    if args.team_worker_history is not None:
        return _cmd_team_worker_history(args.team_worker_history, args.date_from, args.date_to)
    if args.skill_test_all:
        return _cmd_skill_test_all()
    if args.skill_test:
        return _cmd_skill_test_one(args.skill_test)
    if args.skill_review_list:
        return _cmd_skill_review_list()
    if args.dhansetu_ingest_sheet:
        if not (args.sheets_credentials and args.sheets_id):
            print(json.dumps({"error": "--dhansetu-ingest-sheet requires --sheets-credentials and --sheets-id"}))
            return
        return _cmd_dhansetu_ingest_sheet(args.business, args.sheets_credentials, args.sheets_id, args.sheet_name)
    if args.dhansetu_draft_course is not None:
        return _cmd_dhansetu_draft_course(args.dhansetu_draft_course)
    if args.dhansetu_write_prompt is not None:
        return _cmd_dhansetu_write_prompt(args.dhansetu_write_prompt, args.brief)
    if args.dhansetu_write_reel is not None:
        return _cmd_dhansetu_write_reel(args.dhansetu_write_reel, args.brief)
    if args.dhansetu_schedule_post is not None:
        return _cmd_dhansetu_schedule_post(args.dhansetu_schedule_post, args.platform)
    if args.dhansetu_list_courses:
        return _cmd_dhansetu_list_courses(args.business, args.course_status)
    if args.dhansetu_ready_to_post:
        return _cmd_dhansetu_ready_to_post(args.platform)
    if args.pa_refine:
        return _cmd_pa_refine(args.pa_refine, args.business)
    if args.pa_send_to_ceo:
        return _cmd_pa_send_to_ceo(args.pa_send_to_ceo, args.business)
    if args.pa_voice:
        return _cmd_pa_voice(args.pa_voice, args.business, args.pa_voice_gender)
    if args.dhansetu_add_link:
        if not (args.link_title and args.link_url):
            print(json.dumps({"error": "--dhansetu-add-link requires --link-title and --link-url"}))
            return
        return _cmd_dhansetu_add_link(args.business, args.link_title, args.link_url, args.link_order)
    if args.dhansetu_list_links:
        return _cmd_dhansetu_list_links(args.business)
    if args.discovery_start:
        return _cmd_discovery_start(args)
    if args.discovery_analyze is not None:
        return _cmd_discovery_analyze(args.discovery_analyze)
    if args.discovery_list:
        return _cmd_discovery_list(args.discovery_status)
    if args.initiative_add:
        return _cmd_initiative_add(args.initiative_add, args.initiative_artifact_url, track=args.initiative_track)
    if args.milestone_add is not None:
        if not args.milestone_title:
            print(json.dumps({"error": "--milestone-add requires --milestone-title"}))
            return
        return _cmd_milestone_add(args.milestone_add, args.milestone_title, args.milestone_done_on_add)
    if args.milestone_done is not None:
        return _cmd_milestone_done(args.milestone_done)
    if args.initiative_status is not None:
        if not args.initiative_set_status:
            print(json.dumps({"error": "--initiative-status requires --initiative-set-status"}))
            return
        return _cmd_initiative_status(args.initiative_status, args.initiative_set_status)
    if args.initiatives_list:
        return _cmd_initiatives_list()
    if args.failure_analysis_add:
        return _cmd_failure_analysis_add(args.failure_analysis_add)
    if args.failure_analyses_list:
        return _cmd_failure_analyses_list(args.failure_status)
    if args.chat_message:
        return _cmd_chat_message(args.chat_agent, args.chat_message)
    if args.support_bot_ask:
        return _cmd_support_bot_ask(args.support_bot_ask, args.support_email, args.support_name,
                                     args.support_business_id, args.telegram_token, args.telegram_chat_id)

    if args.strategy_add:
        if not (args.strategy_name and args.strategy_symbol and args.strategy_rule_type and args.strategy_params):
            print(json.dumps({"error": "--strategy-add requires --strategy-name, --strategy-symbol, --strategy-rule-type, --strategy-params"}))
            return
        return _cmd_strategy_add(args.strategy_name, args.strategy_symbol, args.strategy_rule_type, args.strategy_params)
    if args.strategies_list:
        return _cmd_strategies_list(None)
    if args.strategy_status is not None:
        if not args.strategy_set_status:
            print(json.dumps({"error": "--strategy-status requires --strategy-set-status"}))
            return
        return _cmd_strategy_status(args.strategy_status, args.strategy_set_status)
    if args.trading_check:
        return _cmd_trading_check()
    if args.trading_positions:
        return _cmd_trading_positions(args.position_status)
    if args.trading_journal:
        return _cmd_trading_journal(args.journal_limit)
    if args.trading_price:
        return _cmd_trading_price(args.trading_price)

    if args.peopledesk_add_staff:
        if not (args.owner_email and args.staff_name):
            print(json.dumps({"error": "--peopledesk-add-staff requires --owner-email and --staff-name"}))
            return
        return _cmd_peopledesk_add_staff(args.owner_email, args.staff_name, args.staff_role, args.staff_phone,
                                          args.staff_pay_type, args.staff_daily_wage, args.staff_monthly_salary,
                                          args.staff_join_date)
    if args.peopledesk_list_staff:
        if not args.owner_email:
            print(json.dumps({"error": "--peopledesk-list-staff requires --owner-email"}))
            return
        return _cmd_peopledesk_list_staff(args.owner_email, args.staff_status)
    if args.peopledesk_mark_attendance:
        if not (args.staff_id and args.attendance_date and args.attendance_status):
            print(json.dumps({"error": "--peopledesk-mark-attendance requires --staff-id, --attendance-date, --attendance-status"}))
            return
        return _cmd_peopledesk_mark_attendance(args.staff_id, args.attendance_date, args.attendance_status)
    if args.peopledesk_payroll:
        if not (args.owner_email and args.date_from and args.date_to):
            print(json.dumps({"error": "--peopledesk-payroll requires --owner-email, --date-from, --date-to"}))
            return
        return _cmd_peopledesk_payroll(args.owner_email, args.date_from, args.date_to)

    if args.knowledge_add:
        return _cmd_knowledge_add(args.knowledge_category, args.knowledge_add, args.content, args.tags)
    if args.knowledge_ask:
        return _cmd_knowledge_ask(args.knowledge_ask, None)
    if args.buddy_chat:
        return _cmd_buddy_chat(args.buddy_chat, args.buddy_mode, args.session_id)
    if args.voice_listen:
        return _cmd_voice_listen(args.seconds, args.owner_passphrase, args.voice_gender, args.voice_mute)
    if args.voice_loop:
        return _cmd_voice_loop(args.window_seconds, args.owner_passphrase, args.voice_gender, args.voice_mute)
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
