"""Local SQLite event bus shared by SHAKTHI agents and the dashboard."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import state_dir

SECRET_PATTERN = re.compile(r"(?i)(password|secret|token|api[_-]?key|merchant[_-]?salt)\s*[:=]\s*\S+")

@dataclass(frozen=True)
class AgentEvent:
    mission_id: str
    source_agent: str
    target_agent: str
    action: str
    status: str
    message: str
    repo: str
    task_id: str | None = None
    severity: str = "INFO"
    subsystem: str = "shakthi_os"
    latency_ms: int | None = None
    data_source: str = "LIVE"
    event_id: str = field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:16].upper()}")
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class EventBus:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or state_dir() / "events.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS agent_events(
              event_id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, mission_id TEXT NOT NULL,
              task_id TEXT, source_agent TEXT NOT NULL, target_agent TEXT NOT NULL,
              action TEXT NOT NULL, status TEXT NOT NULL, severity TEXT NOT NULL,
              subsystem TEXT NOT NULL, latency_ms INTEGER, message TEXT NOT NULL,
              repo TEXT NOT NULL, data_source TEXT NOT NULL, payload TEXT NOT NULL)""")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def publish(self, event: AgentEvent) -> dict[str, Any]:
        record = asdict(event)
        record["message"] = SECRET_PATTERN.sub(lambda m: f"{m.group(1)}=[REDACTED]", record["message"])
        with self._connect() as connection:
            connection.execute("INSERT INTO agent_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                record["event_id"], record["timestamp"], record["mission_id"], record["task_id"],
                record["source_agent"], record["target_agent"], record["action"], record["status"],
                record["severity"], record["subsystem"], record["latency_ms"], record["message"],
                record["repo"], record["data_source"], json.dumps(record, sort_keys=True)))
        return record

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM agent_events ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(row["payload"]) for row in rows]

