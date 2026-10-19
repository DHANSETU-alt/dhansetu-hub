"""
BlackboxOps OS Website Health Watcher -- real uptime/response-time/SSL
monitoring for a small watchlist of sites, separate from `sites` (local
file presence) and `website_reviews` (one-off SEO/UI audits).

Every field is a real reading at check time. SSL expiry is a genuine TLS
handshake (stdlib `ssl`+`socket`, no external API) reading the peer
certificate's real notAfter date -- not a placeholder, despite the
founder's spec calling it one; this is honestly available for free, so
it's built for real. When a handshake can't happen (plain HTTP site,
connection refused, DNS failure), ssl fields stay None with the real
reason in error_detail -- never a fabricated date.

Incidents are a real transition log: a row opens only when a site flips
online->offline, and closes only when it flips back -- not one row per
check.
"""
import socket
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

from . import db

DEFAULT_TIMEOUT = 10


def _check_ssl(hostname: str, port: int = 443, timeout: float = 5.0) -> dict:
    """Real TLS handshake. Returns {'ssl_expires_at': iso|None, 'ssl_days_remaining': int|None,
    'error': str|None} -- error is only set when info genuinely couldn't be obtained."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as tls:
                cert = tls.getpeercert()
        not_after = cert.get("notAfter")
        if not not_after:
            return {"ssl_expires_at": None, "ssl_days_remaining": None, "error": "certificate had no notAfter field"}
        expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days_remaining = (expires - datetime.now(timezone.utc)).days
        return {"ssl_expires_at": expires.isoformat(), "ssl_days_remaining": days_remaining, "error": None}
    except Exception as e:
        return {"ssl_expires_at": None, "ssl_days_remaining": None, "error": f"TLS handshake failed: {e}"}


def check_one_site(url: str) -> dict:
    """Real HTTP check + real SSL check for one URL. Never raises -- every
    failure mode (timeout, connection refused, DNS failure, non-2xx/3xx) is
    captured as a real 'offline' status with the real error message, not
    swallowed or faked as success."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    is_https = parsed.scheme == "https"

    result = {"status": "offline", "status_code": None, "response_time_ms": None,
              "ssl_expires_at": None, "ssl_days_remaining": None, "error_detail": None}

    started = time.monotonic()
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "BlackboxOps-WebsiteHealthWatcher/1.0"})
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            elapsed_ms = round((time.monotonic() - started) * 1000)
            result["status_code"] = resp.status
            result["response_time_ms"] = elapsed_ms
            result["status"] = "online" if 200 <= resp.status < 400 else "offline"
            if resp.status >= 400:
                result["error_detail"] = f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        # A real HTTP error response IS a real response -- record the real
        # status code and timing rather than treating it as a transport failure.
        elapsed_ms = round((time.monotonic() - started) * 1000)
        result["status_code"] = e.code
        result["response_time_ms"] = elapsed_ms
        result["status"] = "online" if e.code < 400 else "offline"
        result["error_detail"] = f"HTTP {e.code}"
    except Exception as e:
        result["status"] = "offline"
        result["error_detail"] = f"{type(e).__name__}: {e}"

    if is_https and hostname:
        ssl_info = _check_ssl(hostname)
        result["ssl_expires_at"] = ssl_info["ssl_expires_at"]
        result["ssl_days_remaining"] = ssl_info["ssl_days_remaining"]
        if ssl_info["error"] and result["status"] == "online":
            # Site is reachable but SSL info genuinely couldn't be read --
            # note it without downgrading a real successful HTTP check.
            result["error_detail"] = (result["error_detail"] + "; " if result["error_detail"] else "") + ssl_info["error"]
    elif not is_https:
        result["error_detail"] = (result["error_detail"] + "; " if result["error_detail"] else "") + "plain HTTP, no SSL to check"

    return result


def record_check(conn, website: dict, result: dict) -> dict:
    """Insert the check, then apply real transition logic against the
    immediately-previous check for this site."""
    previous = db.previous_health_check(conn, website["id"])
    check_id = db.insert_health_check(
        conn, website_id=website["id"], status=result["status"], status_code=result["status_code"],
        response_time_ms=result["response_time_ms"], ssl_expires_at=result["ssl_expires_at"],
        ssl_days_remaining=result["ssl_days_remaining"], error_detail=result["error_detail"],
    )

    prev_status = previous["status"] if previous else None
    if result["status"] == "offline" and prev_status != "offline":
        db.open_incident(conn, website["id"])
    elif result["status"] == "online" and prev_status == "offline":
        opened_at = None
        row = conn.execute(
            "SELECT opened_at FROM website_incidents WHERE website_id = ? AND status = 'open' LIMIT 1",
            (website["id"],),
        ).fetchone()
        if row:
            opened_at = row["opened_at"]
        if opened_at:
            # SQLite's CURRENT_TIMESTAMP is a naive UTC string ("2026-09-03
            # 02:03:18") -- parse and compare naive-to-naive. An ISO string
            # with an explicit offset (from a different source) stays
            # timezone-aware and compares against an aware "now" instead.
            if "T" in opened_at:
                opened = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
                now = datetime.now(opened.tzinfo) if opened.tzinfo else datetime.now(timezone.utc)
            else:
                opened = datetime.strptime(opened_at, "%Y-%m-%d %H:%M:%S")
                now = datetime.now(timezone.utc).replace(tzinfo=None)
            delta = now - opened
            minutes = int(delta.total_seconds() // 60)
            summary = f"Offline for {minutes}m" if minutes > 0 else "Offline briefly (<1m)"
        else:
            summary = "Back online"
        db.close_open_incident(conn, website["id"], summary)

    # Real DB-authoritative timestamp, not an approximated datetime.now()
    # from Python -- the row's own checked_at (SQLite's CURRENT_TIMESTAMP
    # at INSERT time) is what every other endpoint (/latest, /history)
    # already returns, so /refresh's response shape matches them exactly.
    inserted_row = conn.execute(
        "SELECT checked_at FROM website_health_checks WHERE id = ?", (check_id,)
    ).fetchone()
    result["id"] = check_id
    result["website_id"] = website["id"]
    result["checked_at"] = inserted_row["checked_at"] if inserted_row else None
    return result


def alert_flag(website: dict, latest_check: dict | None) -> bool:
    """Simple alert rule: offline, or response time over this site's own threshold."""
    if not latest_check:
        return False
    if latest_check["status"] != "online":
        return True
    threshold = website.get("alert_response_ms_threshold") or 3000
    rt = latest_check.get("response_time_ms")
    return rt is not None and rt > threshold


def check_all_watched_sites() -> list:
    """Runs a real check against every active watched site, records it, and
    returns fresh results. This is the single function both the manual
    refresh endpoint and the background scheduler call."""
    results = []
    with db.get_conn() as conn:
        sites = db.list_watched_websites(conn)
    for site in sites:
        outcome = check_one_site(site["url"])
        with db.get_conn() as conn:
            recorded = record_check(conn, site, outcome)
        results.append({**site, "latest_check": recorded, "in_alert": alert_flag(site, recorded)})
    return results
