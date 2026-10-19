"""Strict pre-authorized policy for unattended Founder Away Mode.

The policy authorizes safe local work only. It never shells out on behalf of an
agent and never converts a denied action into an approval.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from .config import project_root, state_dir


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FounderMode(StrEnum):
    HOME = "HOME"
    AWAY = "AWAY"


class Decision(StrEnum):
    ALLOWED = "ALLOWED"
    WAITING_FOR_FOUNDER = "WAITING_FOR_FOUNDER"


SAFE_ACTIONS = frozenset({
    "read_repo", "write_repo", "create_tests", "run_tests", "lint_typecheck_build",
    "inspect_logs", "inspect_git", "create_local_branch", "commit_local", "inspect_services",
    "local_diagnostics", "read_telemetry", "read_system_status", "update_mission_state",
    "agent_message", "failure_analysis", "retry_safe_strategy", "guardian_observation",
    "bugfix_repo", "prompt_architect", "dashboard_ui", "browser_demo",
})
PROHIBITED_ACTIONS = frozenset({
    "sudo", "root", "install_packages", "sudoers", "firewall", "ssh_settings",
    "system_service", "format_drive", "mount_drive", "unmount_drive", "destructive_filesystem",
    "delete_database", "production_migration", "production_deploy", "dns", "cloudflare",
    "payment_config", "real_payment", "payment_credentials", "oauth_credentials", "secret_rotation",
    "bank_settlement", "external_login", "external_message", "destructive_git", "force_push",
    "delete_repository", "privilege_escalation",
})


@dataclass(frozen=True)
class PolicyDecision:
    decision: str
    action: str
    reason: str
    mode: str
    path: str | None = None


class FounderAwayPolicy:
    def __init__(self, path: Path | None = None):
        self.path = path or state_dir() / "founder_away.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS mode(id INTEGER PRIMARY KEY CHECK(id=1), mode TEXT NOT NULL, changed_at TEXT NOT NULL, changed_by TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS approvals(approval_id TEXT PRIMARY KEY, mission TEXT, task TEXT, action TEXT, exact_change TEXT, why TEXT, risk TEXT, alternatives TEXT, consequence TEXT, status TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS evidence(id INTEGER PRIMARY KEY AUTOINCREMENT, mission TEXT, task TEXT, files_changed TEXT, tests TEXT, build TEXT, runtime TEXT, guardian TEXT, git_status TEXT, commit_id TEXT, created_at TEXT);
            """)
            if not c.execute("SELECT 1 FROM mode WHERE id=1").fetchone():
                c.execute("INSERT INTO mode VALUES(1,?,?,?)", (FounderMode.HOME, now(), "system"))

    def _db(self):
        c = sqlite3.connect(self.path, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    def status(self) -> dict[str, Any]:
        with self._db() as c:
            mode = c.execute("SELECT mode,changed_at,changed_by FROM mode WHERE id=1").fetchone()
            waiting = c.execute("SELECT count(*) FROM approvals WHERE status='WAITING_FOR_FOUNDER'").fetchone()[0]
            evidence = c.execute("SELECT count(*) FROM evidence").fetchone()[0]
        current_missions = 0
        loop_db = state_dir() / "angella_executive.db"
        if loop_db.exists():
            try:
                with sqlite3.connect(loop_db) as loop:
                    current_missions = loop.execute("SELECT count(*) FROM missions WHERE state NOT IN ('COMPLETE','CANCELLED','BLOCKED_EXTERNAL','WAITING_FOR_FOUNDER','FAILED_WITH_ESCALATION')").fetchone()[0]
            except sqlite3.Error:
                current_missions = 0
        guardian = "NOT CONNECTED"
        guardian_file = state_dir() / "guardian_status.json"
        if guardian_file.exists():
            try:
                guardian = json.loads(guardian_file.read_text(encoding="utf-8")).get("state", "UNKNOWN")
            except (OSError, json.JSONDecodeError):
                guardian = "UNKNOWN"
        monitor_state = "NOT RUNNING"
        monitor_file = state_dir() / "founder_sleep_monitor.json"
        if monitor_file.exists():
            try:
                heartbeat = datetime.fromisoformat(json.loads(monitor_file.read_text(encoding="utf-8"))["timestamp"])
                if (datetime.now(timezone.utc) - heartbeat).total_seconds() <= 90:
                    monitor_state = "ACTIVE"
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                monitor_state = "UNKNOWN"
        return {"mode": mode["mode"], "changed_at": mode["changed_at"], "changed_by": mode["changed_by"],
                "angella": "ACTIVE" if mode["mode"] == FounderMode.AWAY else "STANDBY",
                "safe_tasks": "AUTHORIZED" if mode["mode"] == FounderMode.AWAY else "PAUSED",
                "waiting_approval": waiting, "guardian": guardian, "current_missions": current_missions,
                "evidence_records": evidence, "mission_scheduler": monitor_state, "followup_engine": monitor_state,
                "failure_memory": "ACTIVE", "strategy_memory": "ACTIVE", "sentinel": "ACTIVE" if guardian != "NOT CONNECTED" else "NOT CONNECTED",
                "bug_fixer": "READY", "prompt_architect": "READY", "codex_engineering": "IDLE", "policy_version": "1.0.0"}

    def set_mode(self, mode: FounderMode, *, changed_by: str = "Founder") -> dict[str, Any]:
        with self._db() as c:
            c.execute("UPDATE mode SET mode=?,changed_at=?,changed_by=? WHERE id=1", (mode, now(), changed_by))
        return self.status()

    @staticmethod
    def confined_path(path: str | Path) -> Path:
        candidate = Path(path).expanduser().resolve()
        root = project_root().resolve()
        if candidate != root and root not in candidate.parents:
            raise PermissionError(f"path outside authorized repository: {candidate}")
        return candidate

    def authorize(self, action: str, *, path: str | Path | None = None) -> PolicyDecision:
        mode = self.status()["mode"]
        if action in SAFE_ACTIONS:
            safe_path = None
            if path is not None:
                safe_path = str(self.confined_path(path))
            return PolicyDecision(Decision.ALLOWED, action, "pre-authorized safe local policy", mode, safe_path)
        if action in PROHIBITED_ACTIONS or action not in SAFE_ACTIONS:
            return PolicyDecision(Decision.WAITING_FOR_FOUNDER, action, "not in strict pre-authorized allowlist", mode)
        return PolicyDecision(Decision.WAITING_FOR_FOUNDER, action, "denied by policy", mode)

    def request_approval(self, *, mission: str, task: str, action: str, exact_change: str,
                         why: str, risk: str, alternatives: list[str], consequence: str) -> dict[str, Any]:
        approval_id = f"APPROVAL-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        record = {"approval_id": approval_id, "mission": mission, "task": task, "action": action,
                  "exact_change": exact_change, "why": why, "risk": risk,
                  "alternatives": alternatives, "consequence": consequence,
                  "status": Decision.WAITING_FOR_FOUNDER, "created_at": now()}
        with self._db() as c:
            c.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?,?,?,?,?,?)", (approval_id, mission, task, action, exact_change, why, risk, json.dumps(alternatives), consequence, Decision.WAITING_FOR_FOUNDER, record["created_at"]))
        return record

    def evaluate_task(self, *, mission: str, task: str, action: str, exact_change: str = "",
                      why: str = "", risk: str = "UNKNOWN", alternatives: list[str] | None = None,
                      consequence: str = "Task waits for Founder") -> dict[str, Any]:
        """Authorize a task or create its required approval record when denied."""
        decision = self.authorize(action)
        if decision.decision == Decision.ALLOWED:
            return {"decision": decision.decision, "policy": asdict(decision)}
        return self.request_approval(mission=mission, task=task, action=action,
            exact_change=exact_change, why=why or decision.reason, risk=risk,
            alternatives=alternatives or ["continue independent safe tasks", "wait for Founder approval"], consequence=consequence)

    def preflight(self, *, code_changing: bool = False) -> dict[str, str]:
        result = {"git_status": "UNAVAILABLE", "commit_id": "UNAVAILABLE"}
        if not code_changing:
            return result
        try:
            status = subprocess.run(["git", "status", "--short"], cwd=project_root(), capture_output=True, text=True, timeout=3, check=True).stdout.strip()
            commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project_root(), capture_output=True, text=True, timeout=3, check=True).stdout.strip()
            result = {"git_status": status or "CLEAN", "commit_id": commit}
        except (OSError, subprocess.SubprocessError):
            result = {"git_status": "UNAVAILABLE", "commit_id": "UNAVAILABLE"}
        return result

    def record_evidence(self, *, mission: str, task: str, files_changed: list[str], tests: str,
                        build: str, runtime: str, guardian: str, code_changing: bool = False) -> dict[str, Any]:
        preflight = self.preflight(code_changing=code_changing)
        record = {"mission": mission, "task": task, "files_changed": files_changed, "tests": tests,
                  "build": build, "runtime": runtime, "guardian": guardian, **preflight, "created_at": now()}
        with self._db() as c:
            c.execute("INSERT INTO evidence(mission,task,files_changed,tests,build,runtime,guardian,git_status,commit_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (mission, task, json.dumps(files_changed), tests, build, runtime, guardian, preflight["git_status"], preflight["commit_id"], record["created_at"]))
        return record

    def return_brief(self) -> dict[str, Any]:
        with self._db() as c:
            waiting = [dict(r) for r in c.execute("SELECT * FROM approvals WHERE status='WAITING_FOR_FOUNDER' ORDER BY created_at DESC")]
            evidence = [dict(r) for r in c.execute("SELECT * FROM evidence ORDER BY created_at DESC LIMIT 30")]
        for row in waiting: row["alternatives"] = json.loads(row["alternatives"])
        return {"title": "FOUNDER RETURN BRIEF", "completed": evidence, "still_running": [], "waiting_approval": waiting, "failures": [], "strategies_changed": [], "tests": [r["tests"] for r in evidence], "builds": [r["build"] for r in evidence], "security_events": []}
