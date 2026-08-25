"""
WEB-001: external website audit. Deterministic checks only -- same
philosophy as security.py ("a security scanner that depends on a 3B
local model's diligence isn't one"). Counting broken links, grading
security headers, and parsing meta tags don't need model judgment;
stdlib urllib + html.parser is enough, same "no new dependency for a
handful of HTTP calls" precedent as telegram.py.

Reuses the existing `audits`/`audit_findings` tables (built for codebase
audits) rather than adding a parallel schema -- sheets.sync_audit_history()
already syncs any completed `audits` row generically, so a website audit
lands in the same "Audit History" tab for free.
"""
import html.parser
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

from . import config, db


class AuditError(RuntimeError):
    pass


SECURITY_HEADERS = (
    "Strict-Transport-Security", "X-Content-Type-Options", "X-Frame-Options",
    "Content-Security-Policy", "Referrer-Policy",
)

SKIP_LINK_SCHEMES = ("mailto:", "tel:", "javascript:", "#")


class _PageParser(html.parser.HTMLParser):
    """One pass over the homepage HTML collecting everything every check
    below needs, so a 200KB page isn't parsed ten separate times."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta = []
        self.links = []
        self.canonical = None
        self.image_alt_flags = []
        self.h1_count = 0
        self.html_lang = None
        self.form_input_label_flags = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            self.meta.append(d)
        elif tag == "link" and d.get("rel") == "canonical":
            self.canonical = d.get("href")
        elif tag == "a" and d.get("href"):
            self.links.append(d["href"])
        elif tag == "img":
            self.image_alt_flags.append(bool(d.get("alt")))
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "html":
            self.html_lang = d.get("lang")
        elif tag == "input" and d.get("type") not in ("hidden", "submit", "button"):
            self.form_input_label_flags.append(bool(d.get("id") or d.get("aria-label")))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def fetch(url: str, method: str = "GET", timeout: int = None) -> dict:
    timeout = timeout or config.WEBSITE_AUDIT_TIMEOUT_SECONDS
    req = urllib.request.Request(url, method=method, headers={"User-Agent": config.WEBSITE_AUDIT_USER_AGENT})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read() if method == "GET" else b""
            return {"ok": True, "status": resp.status, "headers": dict(resp.headers), "body": body,
                    "elapsed_ms": int((time.monotonic() - start) * 1000), "final_url": resp.url, "error": None}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "headers": dict(e.headers or {}), "body": b"",
                "elapsed_ms": int((time.monotonic() - start) * 1000), "final_url": url, "error": str(e)}
    except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
        return {"ok": False, "status": None, "headers": {}, "body": b"",
                "elapsed_ms": int((time.monotonic() - start) * 1000), "final_url": url, "error": str(e)}


def check_homepage_load(result: dict) -> dict:
    return {"loaded": result["ok"] and result["status"] == 200, "status_code": result["status"],
            "response_time_ms": result["elapsed_ms"], "error": result.get("error")}


def check_https(url: str, result: dict) -> dict:
    uses_https = url.lower().startswith("https://")
    # A GET that succeeds over https:// with no exception means the cert
    # chain validated against the OS trust store (net.enable_system_trust,
    # wired at package import) -- a bad cert would surface here as an
    # SSLError, which urllib wraps in URLError and fetch() already caught
    # as ok=False.
    return {"uses_https": uses_https, "cert_valid": (uses_https and result["ok"]) if uses_https else None}


def check_mobile_responsiveness(page: _PageParser) -> dict:
    viewport = next((m for m in page.meta if m.get("name") == "viewport"), None)
    return {"has_viewport_meta": viewport is not None, "content": viewport.get("content") if viewport else None}


def check_seo_metadata(page: _PageParser) -> dict:
    description = next((m for m in page.meta if m.get("name") == "description"), None)
    og_title = next((m for m in page.meta if m.get("property") == "og:title"), None)
    title = page.title.strip()
    desc_content = (description.get("content") or "").strip() if description else ""
    return {
        "title": title or None, "title_length_ok": 10 <= len(title) <= 60,
        "meta_description": desc_content or None, "description_length_ok": 50 <= len(desc_content) <= 160,
        "h1_count": page.h1_count, "single_h1": page.h1_count == 1,
        "canonical": page.canonical, "has_canonical": page.canonical is not None,
        "has_og_tags": og_title is not None,
    }


def check_accessibility(page: _PageParser) -> dict:
    images_missing_alt = sum(1 for has_alt in page.image_alt_flags if not has_alt)
    unlabeled_inputs = sum(1 for has_label in page.form_input_label_flags if not has_label)
    return {
        "html_lang_present": bool(page.html_lang), "images_total": len(page.image_alt_flags),
        "images_missing_alt": images_missing_alt, "form_inputs_total": len(page.form_input_label_flags),
        "form_inputs_unlabeled": unlabeled_inputs,
    }


def check_security_headers(result: dict) -> dict:
    present = {h: (h in result["headers"]) for h in SECURITY_HEADERS}
    return {"present": present, "missing": [h for h, ok in present.items() if not ok],
            "present_count": sum(present.values()), "total": len(SECURITY_HEADERS)}


def check_broken_links(base_url: str, page: _PageParser) -> dict:
    seen, targets = set(), []
    for href in page.links:
        if href.startswith(SKIP_LINK_SCHEMES):
            continue
        absolute = urllib.parse.urljoin(base_url, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        targets.append(absolute)
        if len(targets) >= config.WEBSITE_AUDIT_MAX_LINKS_CHECKED:
            break

    broken = []
    for link in targets:
        r = fetch(link, method="HEAD", timeout=8)
        if not r["ok"] and r["status"] in (405, None):
            r = fetch(link, method="GET", timeout=8)  # some servers reject HEAD -- retry before flagging
        if not r["ok"]:
            broken.append({"url": link, "status": r["status"], "error": r.get("error")})

    return {"checked": len(targets), "broken": broken, "broken_count": len(broken),
            "skipped_beyond_cap": max(0, len(page.links) - len(targets))}


def check_sitemap(base_url: str) -> dict:
    r = fetch(urllib.parse.urljoin(base_url, "/sitemap.xml"), timeout=8)
    head = r["body"][:2000]
    looks_like_xml = b"<urlset" in head or b"<sitemapindex" in head
    return {"present": r["ok"], "status_code": r["status"], "looks_valid": bool(r["ok"] and looks_like_xml)}


def check_robots_txt(base_url: str) -> dict:
    r = fetch(urllib.parse.urljoin(base_url, "/robots.txt"), timeout=8)
    text = r["body"].decode(errors="ignore") if r["ok"] else ""
    disallow_all = any(line.strip().lower() == "disallow: /" for line in text.splitlines())
    return {"present": r["ok"], "status_code": r["status"],
            "references_sitemap": "sitemap:" in text.lower(), "disallows_everything": disallow_all}


def _score(points_earned: int, points_possible: int) -> int:
    if points_possible == 0:
        return 100
    return max(0, min(100, round(100 * points_earned / points_possible)))


def compute_scores(load, https, mobile, seo, perf_check, links, a11y, headers, sitemap, robots) -> dict:
    seo_earned = sum([
        bool(seo["title"]) and seo["title_length_ok"], bool(seo["meta_description"]) and seo["description_length_ok"],
        seo["single_h1"], seo["has_canonical"], seo["has_og_tags"], sitemap["present"], robots["present"],
    ])
    seo_score = _score(seo_earned, 7)

    security_earned = (40 if (https["uses_https"] and https["cert_valid"]) else 0) + headers["present_count"] * 12
    security_score = _score(security_earned, 100)

    if perf_check["response_time_ms"] < 1000:
        perf_score = 100
    elif perf_check["response_time_ms"] < 2000:
        perf_score = 85
    elif perf_check["response_time_ms"] < 3000:
        perf_score = 70
    elif perf_check["response_time_ms"] < 5000:
        perf_score = 50
    else:
        perf_score = 30

    link_health = 100 if links["checked"] == 0 else _score(links["checked"] - links["broken_count"], links["checked"])
    a11y_penalty = (10 if a11y["images_missing_alt"] else 0) + (10 if not a11y["html_lang_present"] else 0)
    website_health_earned = (
        (100 if load["loaded"] else 0) + (100 if mobile["has_viewport_meta"] else 0)
        + link_health + max(0, perf_score) + max(0, 100 - a11y_penalty)
    )
    website_health_score = _score(website_health_earned, 500)

    return {"website_health_score": website_health_score, "seo_score": seo_score,
            "security_score": security_score, "performance_score": perf_score}


def format_report(url: str, scores: dict, load, https, links, headers, timestamp: str) -> str:
    creds_ok = "Safe" if (https["uses_https"] and https["cert_valid"]) else "Warning"
    return f"""🌐 SHAKTHI WEBSITE AUDIT REPORT

URL: {url}

Website Health Score: {scores['website_health_score']}/100
SEO Score: {scores['seo_score']}/100
Security Score: {scores['security_score']}/100
Performance Score: {scores['performance_score']}/100

Homepage: {"Online" if load["loaded"] else "FAILED"} ({load['response_time_ms']}ms)
HTTPS: {"Yes" if https["uses_https"] else "No"}
Broken Links: {links['broken_count']}/{links['checked']} checked
Security Headers: {headers['present_count']}/{headers['total']} present

Timestamp:
{timestamp}"""


def run_website_audit(url: str, telegram_token: str = None, telegram_chat_id: str = None,
                       sheets_credentials: str = None, sheets_id: str = None,
                       payment_amount_inr: float = None, razorpay_key_id: str = None,
                       razorpay_key_secret: str = None, customer_name: str = None,
                       customer_contact: str = None) -> dict:
    """Offer A (Website Health Audit) end-to-end: run the audit, deliver
    the report, and -- if a price + Razorpay keys are given -- attach a
    real payment link for the audit fee. Payment link creation is
    best-effort: a Razorpay failure never blocks delivering the audit
    itself, same fail-open pattern as the Telegram/Sheets steps below."""
    from datetime import datetime

    home = fetch(url)
    page = _PageParser()
    if home["ok"]:
        try:
            page.feed(home["body"].decode(errors="ignore"))
        except Exception:
            pass  # malformed HTML shouldn't crash the audit -- checks below just see empty page fields

    load = check_homepage_load(home)
    https = check_https(url, home)
    mobile = check_mobile_responsiveness(page)
    seo = check_seo_metadata(page)
    a11y = check_accessibility(page)
    headers = check_security_headers(home)
    links = check_broken_links(url, page) if home["ok"] else {"checked": 0, "broken": [], "broken_count": 0, "skipped_beyond_cap": 0}
    sitemap = check_sitemap(url)
    robots = check_robots_txt(url)

    scores = compute_scores(load, https, mobile, seo, load, links, a11y, headers, sitemap, robots)

    findings = []
    if not load["loaded"]:
        findings.append(("homepage_load", "P0", url, f"Homepage did not load cleanly: {load.get('error') or load['status_code']}"))
    if not https["uses_https"]:
        findings.append(("https", "P0", url, "Site is not served over HTTPS."))
    elif not https["cert_valid"]:
        findings.append(("https", "P1", url, "HTTPS in use but the connection did not validate cleanly."))
    if not mobile["has_viewport_meta"]:
        findings.append(("mobile", "P2", url, "No viewport meta tag found -- page likely isn't mobile-responsive."))
    if not seo["title"]:
        findings.append(("seo", "P1", url, "Missing <title> tag."))
    if not seo["meta_description"]:
        findings.append(("seo", "P2", url, "Missing meta description."))
    if not seo["single_h1"]:
        findings.append(("seo", "P3", url, f"Found {seo['h1_count']} <h1> tags (expected exactly 1)."))
    if not sitemap["present"]:
        findings.append(("sitemap", "P2", url, "sitemap.xml not found."))
    if not robots["present"]:
        findings.append(("robots", "P3", url, "robots.txt not found."))
    elif robots["disallows_everything"]:
        findings.append(("robots", "P1", url, "robots.txt disallows all crawling (Disallow: /)."))
    for h in headers["missing"]:
        findings.append(("security_header", "P2", url, f"Missing security header: {h}"))
    if a11y["images_missing_alt"]:
        findings.append(("accessibility", "P2", url, f"{a11y['images_missing_alt']} of {a11y['images_total']} images missing alt text."))
    if not a11y["html_lang_present"]:
        findings.append(("accessibility", "P3", url, "<html> tag has no lang attribute."))
    for b in links["broken"]:
        findings.append(("broken_link", "P1", b["url"], f"Broken link: {b.get('error') or b['status']}"))

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    report_text = format_report(url, scores, load, https, links, headers, timestamp)
    pages_checked = 1 + links["checked"] + (1 if sitemap["present"] else 0) + (1 if robots["present"] else 0)

    payment_link = None
    payment_error = None
    if payment_amount_inr and razorpay_key_id and razorpay_key_secret:
        from . import payments
        try:
            payment_link = payments.create_payment_link(
                razorpay_key_id, razorpay_key_secret, payment_amount_inr,
                f"Website Health Audit — {url}", customer_name=customer_name,
                customer_contact=customer_contact, reference_id=f"web-audit:{url}",
            )
            report_text += f"\n\nPay for this report (Rs.{payment_amount_inr:.0f}):\n{payment_link['short_url']}"
        except payments.RazorpayError as e:
            payment_error = str(e)

    with db.get_conn() as conn:
        audit_id = db.insert_audit(conn)
        for category, severity, file_path, description in findings:
            db.insert_audit_finding(conn, audit_id, category, severity, file_path, None, description)
        db.complete_audit(conn, audit_id, scores["website_health_score"], len(findings), pages_checked, report_text)
        if payment_link:
            db.insert_payment_link(conn, payment_link["id"], payment_link["short_url"], payment_link["amount_inr"],
                                    f"Website Health Audit — {url}", customer_name=customer_name,
                                    customer_contact=customer_contact, reference_id=f"web-audit:{url}",
                                    status=payment_link["status"])

    result = {
        "audit_id": audit_id, "url": url, "scores": scores, "findings_count": len(findings),
        "pages_checked": pages_checked, "report_text": report_text, "timestamp": timestamp,
        "telegram_sent": False, "sheets_synced": False,
        "payment_link": payment_link["short_url"] if payment_link else None, "payment_error": payment_error,
        "checks": {"homepage_load": load, "https": https, "mobile": mobile, "seo": seo, "accessibility": a11y,
                   "security_headers": headers, "broken_links": links, "sitemap": sitemap, "robots_txt": robots},
    }

    from . import telegram as tg
    from . import telegram_service as ts
    try:
        token, chat_id = ts.resolve_credentials(telegram_token, telegram_chat_id)
        tg.send_message(token, chat_id, report_text, parse_mode=None)
        result["telegram_sent"] = True
    except tg.TelegramError as e:
        result["telegram_error"] = str(e)

    if sheets_credentials and sheets_id:
        from . import sheets
        try:
            state = sheets._load_state()
            client = sheets.get_client(sheets_credentials)
            sheets.sync_audit_history(client, sheets_id, state)
            sheets._save_state(state)
            result["sheets_synced"] = True
        except sheets.SheetsError as e:
            result["sheets_error"] = str(e)
    else:
        result["sheets_error"] = "no Google Sheets credentials provided for this run — DB storage still happened, Sheets did not"

    return result
