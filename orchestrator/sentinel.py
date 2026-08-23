"""
SHAKTHI SENTINEL — Phase v4. Monitors the Mac and SHAKTHI OS itself.

Every field is a real reading at collection time (psutil, live HTTP/DB
checks) -- NULL means "not available on this machine," never a fabricated
placeholder. CPU temperature specifically: `powermetrics --samplers smc`
requires sudo, confirmed unavailable without elevated privileges on this
machine -- reported as None, not guessed. Docker: not installed on this
machine (confirmed in Phase 0.1) -- container status is reported as
"not installed," not silently omitted.
"""
import shutil
import socket
import subprocess
import urllib.request

import psutil

from . import config, db


def _internet_ok(timeout: float = 2.0) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(("8.8.8.8", 53))
        s.close()
        return True
    except OSError:
        return False


def _ollama_ok() -> bool:
    try:
        with urllib.request.urlopen(f"{config.OLLAMA_HOST}/api/tags", timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def _db_ok() -> bool:
    try:
        with db.get_conn() as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False


def _cpu_temp_c():
    """Real attempt, not hardcoded None -- if this ever runs somewhere
    with passwordless sudo configured for powermetrics, it'll work.
    Confirmed unavailable (permission denied) on this machine."""
    try:
        proc = subprocess.run(["powermetrics", "--samplers", "smc", "-n1", "-i1"],
                               capture_output=True, text=True, timeout=5)
        if proc.returncode != 0:
            return None
        for line in proc.stdout.splitlines():
            if "CPU die temperature" in line:
                return float(line.split(":")[1].strip().rstrip("C").strip())
    except Exception:
        pass
    return None


DOCKER_AVAILABLE = shutil.which("docker") is not None


def _score(s: dict) -> tuple:
    health = 100
    if not s["internet_ok"]:
        health -= 30
    if not s["ollama_ok"]:
        health -= 30
    if not s["db_ok"]:
        health -= 40
    if s["disk_percent"] is not None:
        if s["disk_percent"] > 90:
            health -= 20
        elif s["disk_percent"] > 80:
            health -= 10
    if s["battery_percent"] is not None and s["battery_percent"] < 15 and not s["battery_plugged"]:
        health -= 15
    if s["untriaged_errors"] > 10:
        health -= 10
    health = max(0, health)

    perf = 100
    if s["cpu_percent"] is not None:
        if s["cpu_percent"] > 90:
            perf -= 25
        elif s["cpu_percent"] > 75:
            perf -= 10
    if s["ram_percent"] is not None:
        if s["ram_percent"] > 90:
            perf -= 25
        elif s["ram_percent"] > 80:
            perf -= 10
    if s["swap_percent"] is not None and s["swap_percent"] > 50:
        perf -= 15
    perf = max(0, perf)
    return health, perf


def collect_health() -> dict:
    cpu_percent = psutil.cpu_percent(interval=0.3)
    cpu_freq = psutil.cpu_freq()
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    battery = psutil.sensors_battery()

    with db.get_conn() as conn:
        active_tasks = db.active_task_count(conn)
        untriaged = len(db.untriaged_errors(conn, limit=1000))

    snapshot = {
        "cpu_percent": round(cpu_percent, 1),
        "cpu_freq_mhz": round(cpu_freq.current, 0) if cpu_freq else None,
        "cpu_temp_c": _cpu_temp_c(),
        "ram_percent": round(vm.percent, 1),
        "swap_percent": round(swap.percent, 1),
        "disk_percent": round(disk.percent, 1),
        "battery_percent": battery.percent if battery else None,
        "battery_plugged": int(battery.power_plugged) if battery else None,
        "internet_ok": int(_internet_ok()),
        "ollama_ok": int(_ollama_ok()),
        "db_ok": int(_db_ok()),
        "active_tasks": active_tasks,
        "untriaged_errors": untriaged,
    }
    health_score, performance_score = _score(snapshot)
    snapshot["health_score"] = health_score
    snapshot["performance_score"] = performance_score

    with db.get_conn() as conn:
        db.insert_health_snapshot(conn, **snapshot)

    return snapshot


def service_status() -> dict:
    """Qualitative status the numeric snapshot doesn't cover -- each
    honestly reported as configured/reachable or not."""
    return {
        "docker": "installed" if DOCKER_AVAILABLE else "not installed",
        "claude": "configured" if config.ANTHROPIC_API_KEY else "not configured (no ANTHROPIC_API_KEY)",
        "telegram": "credentials are manual-entry only -- run --telegram-test to check",
        "google_sheets": "credentials are manual-entry only -- run --sheets-sync to check",
    }


def classify_status(health_score: int) -> str:
    if health_score >= 80:
        return "Healthy"
    if health_score >= 50:
        return "Warning"
    return "Critical"


def agents_healthy() -> tuple:
    """'Healthy' here means structurally registered and configured (a
    local_model set) -- there is no per-agent runtime crash/uptime tracker
    in this system yet, so this is honestly a registration check, not a
    live health probe per agent. Stated plainly, not implied otherwise."""
    with db.get_conn() as conn:
        agents = db.list_agents(conn)
    healthy = sum(1 for a in agents if a.get("local_model"))
    return healthy, len(agents)


def ceo_summary(snapshot: dict) -> str:
    """One-sentence plain-English summary from the CEO agent. Uses the
    same explicit prose-override this exact agent's role_prompt needed in
    audit.py's executive summary -- without it, the CEO agent's json
    decision-block habit takes over even for a request that isn't a
    decision. That fix, re-applied here rather than re-discovered."""
    from . import bug_fixer
    with db.get_conn() as conn:
        task_id = bug_fixer.new_pipeline_task(conn, "CEO summary for Sentinel health scan (OPS-001)")
        prompt = (
            f"System health snapshot: CPU {snapshot['cpu_percent']}%, RAM {snapshot['ram_percent']}%, "
            f"Disk {snapshot['disk_percent']}%, Ollama {'online' if snapshot['ollama_ok'] else 'offline'}, "
            f"Database {'online' if snapshot['db_ok'] else 'offline'}, health score {snapshot['health_score']}/100.\n\n"
            "IMPORTANT: this is NOT a decision to score. Ignore your usual json decision-block format "
            "completely. Write ONE short plain-English sentence summarizing this for the founder — "
            "no json, no markdown, no code fences."
        )
        text = bug_fixer.call_agent(conn, task_id, "ceo", prompt)
        db.update_task(conn, task_id, "done", text)
    return text.strip()


def format_report(snapshot: dict, agents_healthy_count: int, agents_total: int, summary: str, timestamp: str) -> str:
    status = classify_status(snapshot["health_score"])
    return f"""🖥 SHAKTHI SENTINEL REPORT

CPU: {snapshot['cpu_percent']}%
RAM: {snapshot['ram_percent']}%
Disk: {snapshot['disk_percent']}%

Ollama: {"Online" if snapshot['ollama_ok'] else "Offline"}
Database: {"Online" if snapshot['db_ok'] else "Offline"}

Agents Healthy:
{agents_healthy_count}/{agents_total}

System Health Score:
{snapshot['health_score']}/100

Status:
{status}

Timestamp:
{timestamp}

CEO Summary: {summary}"""


def run_ops_scan(telegram_token: str = None, telegram_chat_id: str = None,
                  sheets_credentials: str = None, sheets_id: str = None) -> dict:
    """OPS-001: Sentinel collects -> CEO summarizes -> Telegram alerts.
    Stored in DB always (collect_health does this); Sheets only if real
    credentials are provided -- reported honestly either way, never
    silently skipped."""
    from datetime import datetime
    from . import telegram as tg
    from . import telegram_service as ts

    snapshot = collect_health()
    healthy, total = agents_healthy()
    summary = ceo_summary(snapshot)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    report_text = format_report(snapshot, healthy, total, summary, timestamp)

    result = {"snapshot": snapshot, "agents_healthy": healthy, "agents_total": total,
              "summary": summary, "report_text": report_text, "telegram_sent": False, "sheets_synced": False}

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
            sheets.sync_system_health(client, sheets_id, state)
            sheets._save_state(state)
            result["sheets_synced"] = True
        except sheets.SheetsError as e:
            result["sheets_error"] = str(e)
    else:
        result["sheets_error"] = "no Google Sheets credentials provided for this run — DB storage still happened, Sheets did not"

    return result
