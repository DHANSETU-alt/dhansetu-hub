"""
SHAKTHI CHROME DEVELOPER BOT.

The "Chrome Developer" persona is an orchestrator, not a new detector --
it composes real, already-built or newly-built deterministic checks:

  - website_audit.py       HTTP-level: HTTPS, security headers, broken
                            links, sitemap/robots (reused, not duplicated)
  - seo_analyzer.py         advanced SEO: heading hierarchy, structured
                            data, Open Graph completeness (new)
  - ui_review_engine.py     real browser-driven checks: load time incl.
                            JS execution, console errors, CTA detection,
                            mobile overflow (new -- urllib can't see any
                            of this)
  - security.py             SECRET_PATTERNS reused to catch API keys
                            leaked in front-end HTML/inline scripts

Workflow: Task Complete (a site exists) -> Website Review -> CEO
deployment-ready gate -> Telegram alert. Integrates with Website Builder
(hooked onto run_full_pipeline(), same additive/non-blocking pattern as
Correction Bot's hook) and Bug Fixer indirectly (P0/P1 findings are the
same severity vocabulary bug_fixer.py uses, ready to escalate later if
that's ever wanted -- not force-escalated here, to avoid scope creep
beyond what was asked).
"""
import re
from datetime import datetime

from . import ceo, config, db, security
from . import seo_analyzer, ui_review_engine
from . import website_audit as wa


def scan_exposed_secrets(html_content: str) -> list:
    """Reuses security.py's SECRET_PATTERNS -- one secret-detector for
    the whole codebase, not a second copy. A website leaking an API key
    in its own front-end JS is a real, common, embarrassing bug."""
    findings = []
    for name, pattern in security.SECRET_PATTERNS.items():
        if pattern.search(html_content):
            findings.append(("security", "P0", f"Possible hardcoded secret exposed in page source ({name})."))
    return findings


def _ui_score(https: dict, headers: dict, links: dict, browser_result: dict | None) -> int:
    earned = 0
    possible = 3
    if https["uses_https"] and https["cert_valid"]:
        earned += 1
    if headers["present_count"] >= 3:
        earned += 1
    if links["checked"] == 0 or links["broken_count"] == 0:
        earned += 1
    if browser_result is not None:
        possible += 2
        if browser_result.get("console_error_count", 0) == 0:
            earned += 1
        if browser_result.get("mobile_renders_without_overflow", True):
            earned += 1
    return max(0, min(100, round(100 * earned / possible)))


def format_report(url: str, seo_score: int, conversion_score: int, ui_score: int,
                   deployment_ready: bool, findings_count: int, timestamp: str) -> str:
    return f"""🖥 SHAKTHI CHROME DEVELOPER REPORT

URL: {url}

SEO Score: {seo_score}/100
Conversion Score: {conversion_score if conversion_score is not None else 'N/A (browser audit unavailable)'}/100
UI Score: {ui_score}/100

Findings: {findings_count}

Deployment Ready:
{"Yes" if deployment_ready else "No"}

Timestamp:
{timestamp}"""


def review_website(url: str, business_id: int = None, telegram_token: str = None,
                    telegram_chat_id: str = None) -> dict:
    with db.get_conn() as conn:
        review_id = db.insert_website_review(conn, url, business_id)

    try:
        home = wa.fetch(url)
        page = wa._PageParser()
        html_content = ""
        if home["ok"]:
            html_content = home["body"].decode(errors="ignore")
            try:
                page.feed(html_content)
            except Exception:
                pass

        https = wa.check_https(url, home)
        headers = wa.check_security_headers(home)
        links = wa.check_broken_links(url, page) if home["ok"] else {"checked": 0, "broken": [], "broken_count": 0, "skipped_beyond_cap": 0}

        seo_analysis = seo_analyzer.analyze(html_content)
        seo_sc = seo_analyzer.seo_score(seo_analysis)
        findings = list(seo_analyzer.seo_findings(seo_analysis))
        findings += scan_exposed_secrets(html_content)
        for h in headers["missing"]:
            findings.append(("security", "P2", f"Missing security header: {h}"))
        for b in links["broken"]:
            findings.append(("performance", "P1", f"Broken link: {b['url']} ({b.get('error') or b['status']})"))

        browser_result = None
        browser_error = None
        try:
            browser_result = ui_review_engine.run_browser_audit(url)
        except ui_review_engine.BrowserAuditError as e:
            browser_error = str(e)

        conversion_sc = ui_review_engine.conversion_score(browser_result) if browser_result else None
        if browser_result:
            findings += ui_review_engine.ui_findings(browser_result)
        elif browser_error:
            findings.append(("performance", "P3", f"Browser-driven checks unavailable: {browser_error}"))

        ui_sc = _ui_score(https, headers, links, browser_result)

        critical_count = sum(1 for f in findings if f[1] in ("P0", "P1"))

        # --- CEO gate: is this deployment-ready? ---
        goal = (
            f"Is {url} ready to deploy/launch as-is? SEO score {seo_sc}/100, UI score {ui_sc}/100, "
            f"conversion score {conversion_sc if conversion_sc is not None else 'unavailable'}/100, "
            f"{len(findings)} findings ({critical_count} critical: P0/P1)."
        )
        try:
            decision = ceo.decide(goal, business_id=business_id)
            deployment_ready = decision.get("status") == "approved"
            decision_reason = decision.get("reason", "")
        except Exception as e:
            deployment_ready = False
            decision_reason = f"CEO decision unavailable, defaulting to not ready: {e}"

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        summary = f"{len(findings)} finding(s) ({critical_count} critical). {decision_reason}"

        with db.get_conn() as conn:
            for category, severity, description in findings:
                db.insert_website_review_finding(conn, review_id, category, severity, description)
            db.complete_website_review(conn, review_id, seo_sc, conversion_sc, ui_sc, deployment_ready,
                                        len(findings), summary)

        report_text = format_report(url, seo_sc, conversion_sc, ui_sc, deployment_ready, len(findings), timestamp)

        result = {
            "review_id": review_id, "url": url, "seo_score": seo_sc, "conversion_score": conversion_sc,
            "ui_score": ui_sc, "deployment_ready": deployment_ready, "findings_count": len(findings),
            "critical_count": critical_count, "report_text": report_text, "timestamp": timestamp,
            "telegram_sent": False, "browser_audit_available": browser_result is not None,
        }

        from . import telegram as tg
        from . import telegram_service as ts
        try:
            token, chat_id = ts.resolve_credentials(telegram_token, telegram_chat_id)
            if critical_count > 0:
                tg.send_message(token, chat_id, tg.format_report_md(f"⚠️ Website errors found on {url}", report_text))
            elif deployment_ready:
                tg.send_message(token, chat_id, tg.format_report_md(f"✅ Deployment ready — {url}", report_text))
            else:
                tg.send_message(token, chat_id, tg.format_report_md("Website audit", report_text))
            result["telegram_sent"] = True
        except tg.TelegramError as e:
            result["telegram_error"] = str(e)

        return result
    except Exception as e:
        with db.get_conn() as conn:
            db.fail_website_review(conn, review_id, str(e))
        raise
