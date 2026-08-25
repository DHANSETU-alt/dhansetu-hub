"""
SHAKTHI Chrome Developer Bot -- real browser-driven UI/conversion checks.

Distinct from website_audit.py: that module is stdlib urllib -- it can
inspect raw HTML but never runs JavaScript, never sees real paint timing,
never catches a console error. This module drives an actual headless
Chromium (via dashboard/scripts/browser_audit.js, using the Playwright
already installed under dashboard/node_modules -- proven this session for
dashboard screenshots) to get data urllib fundamentally cannot: full-page
load time including JS execution, console errors, and whether the page
actually renders sanely at a mobile viewport width.

Live-verified against real sites this session:
  example.com          -> 233ms load, 0 console errors, no CTA
  dhansetuhub.in        -> 9259ms load (vs 4.9s from WEB-001's HTTP-only
                            timing -- JS execution adds real time urllib
                            can't measure), 0 console errors, no CTA found
"""
import json
import subprocess

from . import config

BROWSER_SCRIPT = config.ROOT / "dashboard" / "scripts" / "browser_audit.js"
DEFAULT_TIMEOUT_SECONDS = 30


class BrowserAuditError(RuntimeError):
    pass


def run_browser_audit(url: str, timeout_s: int = DEFAULT_TIMEOUT_SECONDS) -> dict:
    if not BROWSER_SCRIPT.exists():
        raise BrowserAuditError(f"browser_audit.js not found at {BROWSER_SCRIPT}")
    try:
        proc = subprocess.run(
            ["node", str(BROWSER_SCRIPT), url],
            capture_output=True, text=True, timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        raise BrowserAuditError(f"browser audit timed out after {timeout_s}s") from e
    except FileNotFoundError as e:
        raise BrowserAuditError("`node` not found on PATH -- required for browser-driven checks") from e

    if not proc.stdout.strip():
        raise BrowserAuditError(f"browser_audit.js produced no output (stderr: {proc.stderr[:500]})")
    try:
        result = json.loads(proc.stdout.strip().splitlines()[-1])
    except json.JSONDecodeError as e:
        raise BrowserAuditError(f"could not parse browser_audit.js output: {proc.stdout[:500]}") from e

    if not result.get("ok"):
        raise BrowserAuditError(f"browser audit failed: {result.get('error', 'unknown error')}")
    return result


def conversion_score(browser_result: dict) -> int:
    """Deterministic 0-100 score from real browser signals: load time,
    console errors, a detectable call-to-action, and clean mobile
    rendering. Not a Lighthouse-equivalent score (that weighs many more
    signals) -- a focused, honestly-scoped proxy for "will this page
    convert a visitor," built from what this project can actually measure."""
    score = 100
    load_ms = browser_result.get("load_time_ms") or 0
    if load_ms > 5000:
        score -= 30
    elif load_ms > 3000:
        score -= 15
    elif load_ms > 2000:
        score -= 5

    score -= min(30, browser_result.get("console_error_count", 0) * 10)

    if not browser_result.get("has_cta"):
        score -= 20
    if not browser_result.get("mobile_renders_without_overflow", True):
        score -= 20

    return max(0, min(100, score))


def ui_findings(browser_result: dict) -> list:
    findings = []
    load_ms = browser_result.get("load_time_ms") or 0
    if load_ms > 5000:
        findings.append(("performance", "P1", f"Full page load (including JS execution) took {load_ms}ms — well over the ~3s threshold visitors tolerate."))
    elif load_ms > 3000:
        findings.append(("performance", "P2", f"Full page load took {load_ms}ms — worth improving."))

    for err in browser_result.get("console_errors", []):
        findings.append(("console_error", "P1", f"Console error: {err}"))

    if not browser_result.get("has_cta"):
        findings.append(("conversion", "P1", "No clear call-to-action detected (no button/link with buy/sign up/contact/book-style text)."))

    if not browser_result.get("mobile_renders_without_overflow", True):
        findings.append(("mobile", "P1", "Page overflows horizontally at a 390px mobile viewport — likely a responsive layout bug."))

    return findings
