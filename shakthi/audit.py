"""Append-only, hash-chained audit log. Secrets must never be passed here."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import state_dir


class AuditLog:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or state_dir() / "audit.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def entries(self) -> list[dict[str, Any]]:
        return self._records()

    def append(self, *, agent: str, mission_id: str, action: str, reason: str, result: str,
               tools: list[str] | None = None, files_changed: list[str] | None = None,
               approval: str | None = None, rollback_reference: str | None = None) -> dict[str, Any]:
        records = self._records()
        previous_hash = records[-1]["hash"] if records else "GENESIS"
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "mission_id": mission_id,
            "action": action,
            "reason": reason,
            "tools": tools or [],
            "files_changed": files_changed or [],
            "approval": approval,
            "result": result,
            "rollback_reference": rollback_reference,
            "previous_hash": previous_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        payload["hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return payload

    def verify(self) -> bool:
        previous_hash = "GENESIS"
        for record in self._records():
            claimed = record.pop("hash", None)
            if record.get("previous_hash") != previous_hash:
                return False
            canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
            actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            if claimed != actual:
                return False
            previous_hash = claimed
        return True

