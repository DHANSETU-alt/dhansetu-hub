"""Minimal enterprise knowledge graph with typed entities and relationships."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import state_dir


class WorldModel:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or state_dir() / "world_model.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY, type TEXT NOT NULL, name TEXT NOT NULL,
                    attributes TEXT NOT NULL, updated_at TEXT NOT NULL,
                    UNIQUE(type, name)
                );
                CREATE TABLE IF NOT EXISTS relationships (
                    id TEXT PRIMARY KEY, source_id TEXT NOT NULL, relation TEXT NOT NULL,
                    target_id TEXT NOT NULL, evidence TEXT NOT NULL, confidence INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(source_id) REFERENCES entities(id),
                    FOREIGN KEY(target_id) REFERENCES entities(id)
                );
            """)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def add_entity(self, entity_type: str, name: str, attributes: dict[str, Any] | None = None) -> str:
        now = datetime.now(timezone.utc).isoformat()
        entity_id = f"ENT-{uuid.uuid4().hex[:12].upper()}"
        with self._connect() as connection:
            existing = connection.execute("SELECT id FROM entities WHERE type=? AND name=?", (entity_type, name)).fetchone()
            if existing:
                connection.execute("UPDATE entities SET attributes=?, updated_at=? WHERE id=?",
                                   (json.dumps(attributes or {}), now, existing["id"]))
                return existing["id"]
            connection.execute("INSERT INTO entities VALUES (?, ?, ?, ?, ?)",
                               (entity_id, entity_type, name, json.dumps(attributes or {}), now))
        return entity_id

    def entities(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM entities ORDER BY updated_at DESC").fetchall()
        result = []
        for row in rows:
            record = dict(row)
            record["attributes"] = json.loads(record["attributes"])
            result.append(record)
        return result

    def relate(self, source_id: str, relation: str, target_id: str, *, evidence: str, confidence: int) -> str:
        if not evidence.strip():
            raise ValueError("relationships require evidence")
        if not 0 <= confidence <= 100:
            raise ValueError("confidence must be between 0 and 100")
        relationship_id = f"REL-{uuid.uuid4().hex[:12].upper()}"
        with self._connect() as connection:
            connection.execute("INSERT INTO relationships VALUES (?, ?, ?, ?, ?, ?, ?)", (
                relationship_id, source_id, relation, target_id, evidence, confidence,
                datetime.now(timezone.utc).isoformat()))
        return relationship_id

    def neighborhood(self, entity_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("""
                SELECT r.relation, r.evidence, r.confidence,
                       s.id source_id, s.name source_name, s.type source_type,
                       t.id target_id, t.name target_name, t.type target_type
                FROM relationships r JOIN entities s ON s.id=r.source_id
                JOIN entities t ON t.id=r.target_id
                WHERE r.source_id=? OR r.target_id=?
            """, (entity_id, entity_id)).fetchall()
        return [dict(row) for row in rows]

