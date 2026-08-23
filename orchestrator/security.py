"""
Security review. Deterministic checks, not model judgment -- a security
scanner that depends on a 3B local model's diligence isn't one. The Security
agent (agents/security.yaml) only turns these findings into a plain-language
summary; it never decides what counts as a finding.
"""
import json
import re

from . import config, db
from .tools import paths

SECRET_PATTERNS = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "generic_api_key": re.compile(
        r"(?i)(api[_-]?key|secret|token)['\"]?\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"
    ),
    "private_key_header": re.compile(r"-----BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY-----"),
}

RISKY_SITE_PATTERNS = {
    "external_script": re.compile(r"<script[^>]+src=[\"']https?://(?!localhost)", re.IGNORECASE),
    "insecure_form_action": re.compile(r"<form[^>]+action=[\"']http://", re.IGNORECASE),
}

SEVERITY_WEIGHT = {"secret": 25, "site_risk": 10, "permission": 8, "audit": 2}


def _scan_secrets(business_id: int) -> list:
    findings = []
    root = paths.workspace_root(business_id)
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append({"type": "secret", "check": name, "file": str(path.relative_to(root))})
    return findings


def _scan_site_risk(business_id: int) -> list:
    findings = []
    root = paths.workspace_root(business_id)
    for path in root.rglob("*.html"):
        text = path.read_text(errors="ignore")
        for name, pattern in RISKY_SITE_PATTERNS.items():
            if pattern.search(text):
                findings.append({"type": "site_risk", "check": name, "file": str(path.relative_to(root))})
    return findings


def _review_permissions(conn) -> list:
    findings = []
    for agent in db.list_agents(conn):
        tools = json.loads(agent["allowed_tools"] or "[]")
        if "run_command" in tools:
            findings.append({"type": "permission", "check": "run_command_granted", "agent": agent["id"]})
    if config.ALLOW_EXEC:
        findings.append({"type": "permission", "check": "exec_globally_enabled", "agent": None})
    for d in db.recent_tool_calls(conn, limit=20, decision="denied"):
        findings.append({"type": "audit", "check": "denied_tool_call", "agent": d["agent_id"], "tool": d["tool_name"]})
    return findings


def review(business_id: int | None = None) -> dict:
    findings = []
    if business_id is not None:
        findings += _scan_secrets(business_id)
        findings += _scan_site_risk(business_id)

    with db.get_conn() as conn:
        findings += _review_permissions(conn)

        score = 100
        for f in findings:
            score -= SEVERITY_WEIGHT.get(f["type"], 5)
        score = max(0, min(100, score))

        report_id = db.insert_security_report(conn, business_id, score, json.dumps(findings))

    return {"report_id": report_id, "business_id": business_id, "score": score, "findings": findings}


# --- OPS-002: system security posture scan ----------------------------------
#
# Distinct from review() above: review() scans a BUSINESS workspace's
# generated content. This scans the PLATFORM itself -- codebase secrets,
# env var configuration, file permissions, and whether Telegram/Sheets
# credentials are valid. The one rule every function below is written to:
# a security scan must never itself become a leak. Every check here
# returns booleans/status strings, NEVER a secret value, an env var
# value, or file contents -- verified in tests/test_security_posture.py.

import os
import stat as _stat
from pathlib import Path

SENSITIVE_ENV_VARS = ("ANTHROPIC_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
                       "SHAKTHI_OWNER_PASSPHRASE", "SHAKTHI_FAMILY_PASSPHRASE")
RISK_FLAG_ENV_VARS = ("SHAKTHI_ALLOW_EXEC", "SHAKTHI_TOOLS_DRY_RUN")


def scan_api_key_exposure() -> list:
    """Reuses audit.py's exact codebase secret-pattern scan -- one
    detector, not two copies that could drift. Scans orchestrator/**/*.py
    (the platform's own source), not business-generated content -- that's
    review()'s job, above."""
    from . import audit as audit_mod
    files = audit_mod._python_files()
    sources = audit_mod._read_all(files)
    return [f for f in audit_mod.check_security(sources) if f["category"] == "security"]


def scan_env_vars() -> dict:
    """Which sensitive env vars are SET -- never their values. A security
    report that leaks the secrets it's auditing would be a real incident."""
    return {
        "configured": {name: bool(os.environ.get(name)) for name in SENSITIVE_ENV_VARS},
        "risk_flags": {name: os.environ.get(name) == "1" for name in RISK_FLAG_ENV_VARS},
    }


def scan_file_permissions() -> list:
    """Octal permission bits on sensitive local files -- the SQLite DB,
    a .env if present, a Sheets service-account file if its path is set
    via SHAKTHI_SHEETS_CREDENTIALS. Flags group/world-readable, which on
    a shared machine would let another local user read the DB or key
    material directly off disk."""
    findings = []
    candidates = [Path(config.DB_PATH)]
    env_creds_path = os.environ.get("SHAKTHI_SHEETS_CREDENTIALS")
    if env_creds_path:
        candidates.append(Path(env_creds_path))
    dotenv = config.ROOT / ".env"
    if dotenv.exists():
        candidates.append(dotenv)

    for path in candidates:
        if not path.exists():
            continue
        mode = path.stat().st_mode
        if mode & _stat.S_IROTH:
            findings.append({"file": str(path), "issue": "world-readable", "severity": "high"})
        elif mode & _stat.S_IRGRP:
            findings.append({"file": str(path), "issue": "group-readable", "severity": "medium"})
    return findings


def check_telegram_credentials(token: str = None, chat_id: str = None) -> dict:
    """Never returns the token/chat_id -- only whether credentials were
    provided for this scan and whether they're actually valid (a real
    getMe() call, not just presence)."""
    from . import telegram as tg
    from . import telegram_service as ts
    try:
        resolved_token, resolved_chat_id = ts.resolve_credentials(token, chat_id)
    except tg.TelegramError:
        return {"provided": False, "valid": None}
    try:
        tg.get_me(resolved_token)
        return {"provided": True, "valid": True}
    except tg.TelegramError:
        return {"provided": True, "valid": False}


def check_sheets_credentials(credentials_path: str = None) -> dict:
    """Structural validity + file permission only -- reads the JSON to
    confirm it LOOKS like a service account key (type + private_key
    fields present), but the parsed content is never stored or returned,
    only two booleans derived from it."""
    if not credentials_path:
        return {"provided": False, "valid": None, "file_permission_ok": None}
    path = Path(credentials_path)
    if not path.exists():
        return {"provided": True, "valid": False, "file_permission_ok": None}
    try:
        data = json.loads(path.read_text())
        valid = data.get("type") == "service_account" and "private_key" in data
    except (json.JSONDecodeError, OSError):
        valid = False
    mode = path.stat().st_mode
    permission_ok = not bool(mode & _stat.S_IROTH)
    return {"provided": True, "valid": valid, "file_permission_ok": permission_ok}


def _recommend_action(api_key_findings, perm_findings, env_report, tg_status, sheets_status) -> str:
    actions = []
    if api_key_findings:
        actions.append("Remove hardcoded secrets from the codebase immediately.")
    if any(f["severity"] == "high" for f in perm_findings):
        actions.append("Restrict permissions on world-readable sensitive files (chmod 600).")
    if env_report["risk_flags"].get("SHAKTHI_ALLOW_EXEC"):
        actions.append("SHAKTHI_ALLOW_EXEC is enabled — confirm this is intentional.")
    if tg_status["provided"] and tg_status["valid"] is False:
        actions.append("Telegram credentials were provided but are invalid — verify the bot token.")
    if sheets_status["provided"] and sheets_status["valid"] is False:
        actions.append("Google Sheets credentials were provided but are invalid — verify the service account file.")
    return " ".join(actions) if actions else "No action needed — posture is healthy."


def security_posture_scan(telegram_token: str = None, telegram_chat_id: str = None,
                           sheets_credentials: str = None, sheets_id: str = None) -> dict:
    """OPS-002: Sentinel-style live scan, but for security posture instead
    of system health. Stored in DB always (security_reports, business_id
    NULL = platform-wide); Sheets only if real credentials are given,
    reported honestly either way."""
    from datetime import datetime

    api_key_findings = scan_api_key_exposure()
    env_report = scan_env_vars()
    perm_findings = scan_file_permissions()
    tg_status = check_telegram_credentials(telegram_token, telegram_chat_id)
    sheets_status = check_sheets_credentials(sheets_credentials)

    critical = len(api_key_findings) + sum(1 for f in perm_findings if f["severity"] == "high")
    warnings = sum(1 for f in perm_findings if f["severity"] == "medium")
    if env_report["risk_flags"].get("SHAKTHI_ALLOW_EXEC"):
        warnings += 1
    if tg_status["provided"] and tg_status["valid"] is False:
        warnings += 1
    if sheets_status["provided"] and sheets_status["valid"] is False:
        warnings += 1

    score = max(0, 100 - critical * 25 - warnings * 10)
    credentials_status = "Warning" if (
        (tg_status["provided"] and not tg_status["valid"]) or (sheets_status["provided"] and not sheets_status["valid"])
    ) else "Safe"
    recommended_action = _recommend_action(api_key_findings, perm_findings, env_report, tg_status, sheets_status)

    findings_payload = {
        "api_key_findings": api_key_findings, "env_report": env_report,
        "permission_findings": perm_findings, "telegram": tg_status, "sheets": sheets_status,
    }

    # security_reports.findings is a flat list of {type, check, file} dicts
    # everywhere else (review() below, the dashboard's Security page, the
    # API) -- persist that same shape here too, not the richer nested
    # findings_payload above. Found live: the dashboard's Security page
    # crashed (findings.map is not a function) because this scan's row had
    # a dict where every other row has a list.
    flat_findings = (
        [{"type": "api_key_exposure", "check": f["description"], "file": f.get("file_path")} for f in api_key_findings]
        + [{"type": "file_permission", "check": f["issue"], "file": f["file"]} for f in perm_findings]
        + ([{"type": "env_risk", "check": "SHAKTHI_ALLOW_EXEC_enabled", "file": None}]
           if env_report["risk_flags"].get("SHAKTHI_ALLOW_EXEC") else [])
        + ([{"type": "credential", "check": "telegram_invalid", "file": None}]
           if tg_status["provided"] and tg_status["valid"] is False else [])
        + ([{"type": "credential", "check": "sheets_invalid", "file": None}]
           if sheets_status["provided"] and sheets_status["valid"] is False else [])
    )

    with db.get_conn() as conn:
        report_id = db.insert_security_report(conn, None, score, json.dumps(flat_findings))

    report_text = f"""🛡 SHAKTHI SECURITY REPORT

Security Score: {score}/100

Critical Findings: {critical}
Warnings: {warnings}

Credentials Status:
{credentials_status}

Recommended Action:
{recommended_action}"""

    result = {
        "report_id": report_id, "score": score, "critical": critical, "warnings": warnings,
        "credentials_status": credentials_status, "recommended_action": recommended_action,
        "findings": findings_payload, "report_text": report_text,
        "telegram_sent": False, "sheets_synced": False,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
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
            sheets.sync_security_history(client, sheets_id, state)
            sheets._save_state(state)
            result["sheets_synced"] = True
        except sheets.SheetsError as e:
            result["sheets_error"] = str(e)
    else:
        result["sheets_error"] = "no Google Sheets credentials provided for this run — DB storage still happened, Sheets did not"

    return result
