"""
AI WATCHDOG — behavioral/runtime anomaly detection, "double security" on
top of security.py (static posture: secrets, permissions, env config) and
sentinel.py (resource health). This watches PATTERNS over time instead of
point-in-time state: denied-tool-call spikes, cost-ledger spend spikes,
listening ports outside the known allowlist, repeated Voice Commander
denials (brute-force-style probing), and tamper-evidence on the platform's
own critical source files.

Deterministic checks only, same reasoning as security.py's own header
comment: an anomaly detector that depends on a 3B local model's judgment
isn't a reliable one. Every check here returns real, computed findings or
nothing — never a fabricated placeholder.

File-tamper attribution: a changed hash on a watched file is cross-checked
against `git status --porcelain` in the same repo. A change that matches a
file git already shows as modified is attributable to an in-progress edit
(severity "info" — someone is working on it, expected). A change to a file
git shows as CLEAN is unattributable — the file differs from what's on
disk vs. what the DB last hashed, but nothing in the working tree explains
why (severity "critical" — investigate immediately). This is what makes it
a watchdog and not a naive hash-diff: it uses git as the "who did this"
signal instead of alerting on every routine dev edit equally.
"""
import hashlib
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import psutil

from . import config, db

# Ports this machine's own services are known to bind -- dashboard (3000),
# orchestrator API (8787), Ollama (11434), and the sibling blackboxops-os
# project's dev server (8789, moved off Wrangler's default specifically to
# avoid colliding with 8787 here -- see blackboxops-os's own wrangler.toml).
# A LISTEN socket on anything else, bound on this machine, is a real signal
# worth a human look -- not proof of compromise, but not silently ignored.
KNOWN_PORTS = {3000, 8787, 11434, 8789}

# Critical platform source files this watchdog fingerprints. Deliberately
# a fixed list, not "every .py file" -- these are the files whose silent
# tampering would matter most: the CEO gate, the tool permission model,
# the security/watchdog code itself, and the schema it all runs on.
WATCHED_FILES = [
    "orchestrator/ceo.py",
    "orchestrator/security.py",
    "orchestrator/watchdog.py",
    "orchestrator/access.py",
    "orchestrator/db.py",
    "orchestrator/config.py",
    "orchestrator/governor.py",
    "orchestrator/alerts.py",
    "orchestrator/telegram.py",
    "orchestrator/telegram_service.py",
    "db/schema.sql",
    "orchestrator/tools/registry.py",
]

DENIED_CALL_WINDOW_MIN = 30
DENIED_CALL_THRESHOLD = 5
COST_SPIKE_WINDOW_MIN = 30
COST_SPIKE_THRESHOLD_USD = 1.0
VOICE_DENIAL_WINDOW_MIN = 30
VOICE_DENIAL_THRESHOLD = 3


def scan_wifi(state: dict) -> list:
    """Best-effort macOS Wi-Fi privacy/availability check.

    Stores only the last SSID in watchdog state (never credentials). A changed
    SSID is informational because hotel captive portals and roaming are normal;
    a disconnected interface is a warning. Non-macOS or restricted hosts are
    reported as info rather than silently skipped.
    """
    try:
        proc = subprocess.run(
            ["networksetup", "-getairportnetwork", "en0"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return [{"category": "wifi_health", "severity": "info",
                 "detail": f"Wi-Fi status unavailable: {e}"}]

    output = (proc.stdout or proc.stderr).strip()
    if "Current Wi-Fi Network:" not in output:
        return [{"category": "wifi_health", "severity": "warning",
                 "detail": "Wi-Fi is not connected -- hotel network/captive portal may require attention"}]

    ssid = output.split("Current Wi-Fi Network:", 1)[1].strip()
    if not ssid:
        return [{"category": "wifi_health", "severity": "warning",
                 "detail": "Wi-Fi reports no active network"}]

    previous = state.get("watchdog_wifi_ssid")
    state["watchdog_wifi_ssid"] = ssid
    if previous and previous != ssid:
        return [{"category": "wifi_health", "severity": "info",
                 "detail": f"Wi-Fi network changed from {previous!r} to {ssid!r}; verify this is the intended hotel network"}]
    return []


def _sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _git_dirty_paths() -> set | None:
    """Relative paths git currently shows as modified/staged/untracked in
    this repo. None (not empty set) if git itself isn't available/failed --
    callers must treat that as 'can't attribute, be conservative', not
    'nothing is dirty'."""
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"], cwd=config.ROOT,
            capture_output=True, text=True, timeout=5,
        )
        if proc.returncode != 0:
            return None
        return {line[3:].strip() for line in proc.stdout.splitlines() if line.strip()}
    except Exception:
        return None


def scan_file_integrity(conn) -> list:
    findings = []
    dirty = _git_dirty_paths()
    for rel in WATCHED_FILES:
        path = config.ROOT / rel
        current = _sha256_file(path)
        if current is None:
            continue  # file missing -- not this check's job to flag that
        stored = db.get_file_hash(conn, rel)
        if stored is None:
            db.set_file_hash(conn, rel, current)  # bootstrap baseline, no event
            continue
        if current != stored:
            attributable = dirty is not None and rel in dirty
            severity = "info" if attributable else "critical"
            detail = (
                f"{rel} changed (matches current git working-tree edit -- attributable)"
                if attributable else
                f"{rel} changed OUTSIDE the current git working tree -- not attributable "
                f"to an in-progress edit. Investigate immediately."
            )
            findings.append({"category": "file_tamper", "severity": severity, "detail": detail})
            db.set_file_hash(conn, rel, current)
    return findings


def scan_denied_tool_calls(conn) -> list:
    cutoff = (datetime.utcnow() - timedelta(minutes=DENIED_CALL_WINDOW_MIN)).strftime("%Y-%m-%d %H:%M:%S")
    rows = db.recent_tool_calls(conn, limit=500, decision="denied")
    recent = [r for r in rows if r["created_at"] >= cutoff]
    if len(recent) < DENIED_CALL_THRESHOLD:
        return []
    by_agent = {}
    for r in recent:
        by_agent[r["agent_id"]] = by_agent.get(r["agent_id"], 0) + 1
    breakdown = ", ".join(f"{a}: {n}" for a, n in sorted(by_agent.items(), key=lambda kv: -kv[1]))
    return [{
        "category": "denied_spike", "severity": "warning",
        "detail": f"{len(recent)} denied tool calls in the last {DENIED_CALL_WINDOW_MIN}min ({breakdown})",
    }]


def scan_cost_spike(conn, state: dict) -> list:
    since_id = state.get("watchdog_cost_last_id", 0)
    rows = db.cost_ledger_since(conn, since_id)
    if not rows:
        return []
    state["watchdog_cost_last_id"] = max(r["id"] for r in rows)
    cutoff = (datetime.utcnow() - timedelta(minutes=COST_SPIKE_WINDOW_MIN)).strftime("%Y-%m-%d %H:%M:%S")
    recent_spend = sum(r["cost_usd"] or 0.0 for r in rows if r["created_at"] >= cutoff)
    if recent_spend < COST_SPIKE_THRESHOLD_USD:
        return []
    cloud_rows = [r for r in rows if r["provider"] == "claude" and r["created_at"] >= cutoff]
    return [{
        "category": "cost_spike", "severity": "warning",
        "detail": (f"${recent_spend:.2f} spent in the last {COST_SPIKE_WINDOW_MIN}min "
                    f"({len(cloud_rows)} cloud call(s)) -- above the ${COST_SPIKE_THRESHOLD_USD:.2f} watchdog threshold"),
    }]


def scan_voice_probing(conn) -> list:
    cutoff = (datetime.utcnow() - timedelta(minutes=VOICE_DENIAL_WINDOW_MIN)).strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        "SELECT * FROM voice_commands WHERE denied_reason IS NOT NULL AND created_at >= ? ORDER BY id DESC",
        (cutoff,),
    ).fetchall()
    if len(rows) < VOICE_DENIAL_THRESHOLD:
        return []
    return [{
        "category": "voice_probe", "severity": "critical",
        "detail": f"{len(rows)} denied Voice Commander attempts in the last {VOICE_DENIAL_WINDOW_MIN}min -- possible unauthorized access attempt",
    }]


def scan_unexpected_ports() -> list:
    """LISTEN sockets on this machine outside KNOWN_PORTS. Best-effort --
    psutil.net_connections() can raise PermissionError without elevated
    privileges on macOS; reported as 'not available', never silently
    skipped, same pattern as sentinel.py's _cpu_temp_c()."""
    try:
        conns = psutil.net_connections(kind="inet")
    except (PermissionError, psutil.AccessDenied):
        return [{
            "category": "unexpected_port", "severity": "info",
            "detail": "port scan unavailable without elevated privileges on this machine -- not checked this run",
        }]
    except Exception as e:
        return [{"category": "unexpected_port", "severity": "info", "detail": f"port scan failed: {e}"}]

    unexpected = set()
    for c in conns:
        if c.status != psutil.CONN_LISTEN or not c.laddr:
            continue
        port = c.laddr.port
        if port not in KNOWN_PORTS and port >= 1024:  # skip well-known system/OS ports below 1024
            unexpected.add(port)
    if not unexpected:
        return []
    return [{
        "category": "unexpected_port", "severity": "warning",
        "detail": f"unexpected listening port(s) found: {sorted(unexpected)} -- not in the known allowlist {sorted(KNOWN_PORTS)}",
    }]


def run_scan(state: dict) -> dict:
    """Runs every check, persists every real finding to watchdog_events
    (always -- an audit trail exists whether or not anything alerts), and
    returns a summary. state is the shared .alerts_sync_state.json dict --
    only this function's own 'watchdog_cost_last_id' key is read/written
    here; the caller is responsible for loading/saving the file."""
    all_findings = []
    with db.get_conn() as conn:
        all_findings += scan_file_integrity(conn)
        all_findings += scan_denied_tool_calls(conn)
        all_findings += scan_cost_spike(conn, state)
        all_findings += scan_voice_probing(conn)
        all_findings += scan_unexpected_ports()
        all_findings += scan_wifi(state)

        for f in all_findings:
            db.insert_watchdog_event(conn, f["category"], f["severity"], f["detail"])

    critical = sum(1 for f in all_findings if f["severity"] == "critical")
    warning = sum(1 for f in all_findings if f["severity"] == "warning")
    info = sum(1 for f in all_findings if f["severity"] == "info")

    return {
        "findings": all_findings, "critical": critical, "warning": warning, "info": info,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


def format_report(result: dict) -> str:
    status = "CRITICAL" if result["critical"] else ("WARNING" if result["warning"] else "Clear")
    lines = [f"🐕 SHAKTHI WATCHDOG REPORT", "", f"Status: {status}",
             f"Critical: {result['critical']}  Warning: {result['warning']}  Info: {result['info']}", ""]
    for f in result["findings"]:
        if f["severity"] in ("critical", "warning"):
            lines.append(f"[{f['severity'].upper()}] {f['category']}: {f['detail']}")
    if result["critical"] == 0 and result["warning"] == 0:
        lines.append("No anomalies above info level.")
    lines += ["", f"Timestamp: {result['timestamp']}"]
    return "\n".join(lines)
