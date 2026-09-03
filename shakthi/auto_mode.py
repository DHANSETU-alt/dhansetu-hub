"""Governed Linux Founder Auto Mode and operational audit primitives.

Auto Mode is deliberately policy-first: it can authorize safe local work and
read-only remote inspection, but it never grants itself credentials or
executes high-risk external changes.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from .config import state_dir


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AutoMode(StrEnum):
    OFF = "OFF"
    REVIEW = "REVIEW"
    AUTO = "AUTO"
    SLEEP = "SLEEP"


class Risk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionDecision(StrEnum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    WAITING_FOR_FOUNDER = "WAITING_FOR_FOUNDER"


SAFE_READ = frozenset({
    "inspect_cloudflare", "inspect_domain", "inspect_dns", "capture_screenshot",
    "inspect_repo", "inspect_logs", "verify_dns", "verify_http",
})
SAFE_LOCAL = frozenset({
    "read_repo", "write_repo", "create_tests", "run_tests", "lint_typecheck_build",
    "inspect_git", "create_local_branch", "commit_local", "restart_user_service",
    "update_task_state", "agent_message", "failure_analysis", "guardian_observation",
})
MEDIUM_EXTERNAL = frozenset({"change_routine_dns", "correct_nameservers", "trigger_redeploy"})
HIGH_EXTERNAL = frozenset({
    "delete_dns_zone", "change_dnssec", "delete_project", "change_payment_credentials",
    "change_oauth_credentials", "move_registrar", "production_deploy",
})


@dataclass(frozen=True)
class Decision:
    action: str
    decision: str
    risk: str
    mode: str
    reason: str


class AutoModePolicy:
    """Persistent allowlist with non-blocking approval records."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or state_dir() / "auto_mode.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS mode(id INTEGER PRIMARY KEY CHECK(id=1), mode TEXT NOT NULL, changed_at TEXT NOT NULL, changed_by TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY, mission TEXT, task TEXT, action TEXT, exact_change TEXT, why TEXT, risk TEXT, alternatives TEXT, consequence TEXT, status TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS audit(action_id TEXT PRIMARY KEY, mission TEXT, task TEXT, agent TEXT, timestamp TEXT, target TEXT, action TEXT, risk TEXT, before_state TEXT, after_state TEXT, verification TEXT, rollback TEXT, result TEXT);
            """)
            c.execute("INSERT OR IGNORE INTO mode VALUES(1,?,?,?)", (AutoMode.AUTO, now(), "system"))

    def db(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    def mode(self) -> AutoMode:
        with self.db() as c:
            return AutoMode(c.execute("SELECT mode FROM mode WHERE id=1").fetchone()[0])

    def set_mode(self, mode: AutoMode, changed_by: str = "Founder") -> AutoMode:
        with self.db() as c:
            c.execute("UPDATE mode SET mode=?,changed_at=?,changed_by=? WHERE id=1", (mode, now(), changed_by))
        return mode

    def decide(self, action: str, risk: Risk | str | None = None) -> Decision:
        mode = self.mode()
        if action in SAFE_READ:
            return Decision(action, ActionDecision.ALLOW, Risk.LOW, mode, "read-only inspection")
        if action in SAFE_LOCAL:
            return Decision(action, ActionDecision.ALLOW if mode in {AutoMode.AUTO, AutoMode.SLEEP} else ActionDecision.REVIEW, Risk.LOW, mode, "pre-authorized local action")
        if action in MEDIUM_EXTERNAL:
            r = Risk.MEDIUM
            if mode in {AutoMode.AUTO, AutoMode.SLEEP}:
                return Decision(action, ActionDecision.ALLOW, r, mode, "medium action allowed only with rollback and evidence")
            return Decision(action, ActionDecision.REVIEW, r, mode, "review mode requires Founder review")
        r = Risk(risk or (Risk.CRITICAL if action in HIGH_EXTERNAL else Risk.HIGH))
        return Decision(action, ActionDecision.WAITING_FOR_FOUNDER, r, mode, "high-risk or unclassified external action")

    def approval(self, *, mission: str, task: str, action: str, exact_change: str, why: str,
                 risk: str, alternatives: list[str], consequence: str) -> dict[str, Any]:
        rec = {"id": f"APPROVAL-{uuid.uuid4().hex[:12].upper()}", "mission": mission, "task": task,
               "action": action, "exact_change": exact_change, "why": why, "risk": risk,
               "alternatives": alternatives, "consequence": consequence,
               "status": ActionDecision.WAITING_FOR_FOUNDER, "created_at": now()}
        with self.db() as c:
            c.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?,?,?,?,?,?)", (rec["id"], mission, task, action, exact_change, why, risk, json.dumps(alternatives), consequence, rec["status"], rec["created_at"]))
        return rec

    def audit(self, *, mission: str, task: str, agent: str, target: str, action: str,
              risk: str, before_state: Any, after_state: Any, verification: str,
              rollback: str, result: str) -> dict[str, Any]:
        rec = {"action_id": f"ACTION-{uuid.uuid4().hex[:12].upper()}", "mission": mission, "task": task,
               "agent": agent, "timestamp": now(), "target": target, "action": action, "risk": risk,
               "before_state": before_state, "after_state": after_state, "verification": verification,
               "rollback": rollback, "result": result}
        with self.db() as c:
            c.execute("INSERT INTO audit VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", tuple(json.dumps(rec[k]) if isinstance(rec[k], (dict, list)) else rec[k] for k in ("action_id","mission","task","agent","timestamp","target","action","risk","before_state","after_state","verification","rollback","result")))
        return rec

    def status(self) -> dict[str, Any]:
        with self.db() as c:
            waiting = c.execute("SELECT count(*) FROM approvals WHERE status=?", (ActionDecision.WAITING_FOR_FOUNDER,)).fetchone()[0]
            counts = {r[0]: r[1] for r in c.execute("SELECT result,count(*) FROM audit GROUP BY result")}
        return {"mode": self.mode(), "running": "ACTIVE" if self.mode() in {AutoMode.AUTO, AutoMode.SLEEP} else "OFF", "waiting_founder": waiting, "audit_results": counts, "policy_version": "1.0.0"}

