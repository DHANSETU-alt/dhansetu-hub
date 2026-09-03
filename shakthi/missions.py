"""Angela mission creation and persistence."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .audit import AuditLog
from .config import state_dir
from .governance import AutonomyLevel, TruthState, next_confidence_action


@dataclass(frozen=True)
class Confidence:
    decision: int
    evidence: int
    security: int
    execution: int
    business: int

    def __post_init__(self) -> None:
        for value in asdict(self).values():
            if not 0 <= value <= 100:
                raise ValueError("confidence values must be between 0 and 100")

    @property
    def overall(self) -> int:
        return round(sum(asdict(self).values()) / 5)


@dataclass(frozen=True)
class Mission:
    objective: str
    business_impact: str
    priority: str
    project: str
    department: str
    agents: list[str]
    budget: dict[str, float | str]
    estimated_compute_cost: dict[str, float | str]
    dependencies: list[str]
    risk: str
    security_classification: str
    autonomy_level: AutonomyLevel
    rollback_plan: str
    testing_requirements: list[str]
    success_criteria: list[str]
    confidence: Confidence
    mission_id: str = field(default_factory=lambda: f"MISSION-{uuid.uuid4().hex[:12].upper()}")
    current_status: TruthState = TruthState.PLANNED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_record(self) -> dict:
        value = asdict(self)
        value["autonomy_level"] = self.autonomy_level.name
        value["current_status"] = self.current_status.value
        value["confidence"]["overall"] = self.confidence.overall
        value["confidence"]["required_action"] = next_confidence_action(self.confidence.overall)
        return value


class MissionStore:
    def __init__(self, path: Path | None = None, audit: AuditLog | None = None) -> None:
        self.path = path or state_dir() / "control_plane.db"
        self.audit = audit or AuditLog()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS missions (mission_id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL)")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def create(self, mission: Mission) -> dict:
        record = mission.to_record()
        with self._connect() as connection:
            connection.execute("INSERT INTO missions VALUES (?, ?, ?)",
                               (mission.mission_id, json.dumps(record), mission.created_at))
        self.audit.append(agent="Angela Executive Command Center", mission_id=mission.mission_id,
                          action="MISSION_CREATED", reason=mission.objective, result=TruthState.PLANNED.value)
        return record

    def get(self, mission_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute("SELECT payload FROM missions WHERE mission_id=?", (mission_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM missions ORDER BY created_at DESC").fetchall()
        return [json.loads(row[0]) for row in rows]

