"""Adapter from the existing task/event runtime to graph-safe live flow data."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import project_root
from .event_bus import EventBus


ACTIVE_SECONDS = 300


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)
    except ValueError:
        return None


def _age_seconds(value: str | None, now: datetime) -> float | None:
    parsed = _parse(value)
    return max(0, (now - parsed.astimezone(timezone.utc)).total_seconds()) if parsed else None


class LiveFlowAdapter:
    def __init__(self, db_path: Path | None = None, registry_path: Path | None = None, bus: EventBus | None = None) -> None:
        self.db_path = db_path or project_root() / "database" / "shakthi.db"
        self.registry_path = registry_path or project_root() / "agents" / "recruitment" / "agent_registry.json"
        self.bus = bus or EventBus()

    def _agents(self) -> list[dict[str, Any]]:
        if not self.registry_path.exists():
            return []
        return json.loads(self.registry_path.read_text(encoding="utf-8")).get("agents", [])

    def snapshot(self, now: datetime | None = None) -> dict[str, Any]:
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        agents = self._agents()
        task_rows: list[sqlite3.Row] = []
        event_rows: list[sqlite3.Row] = []
        if self.db_path.exists():
            connection = sqlite3.connect(self.db_path)
            connection.row_factory = sqlite3.Row
            try:
                task_rows = connection.execute(
                    "SELECT id,title,assigned_to,status,progress,updated_at,error FROM tasks ORDER BY updated_at DESC"
                ).fetchall()
                event_rows = connection.execute("""
                    SELECT e.id,e.task_id,e.event_type,e.message,e.created_at,
                           t.assigned_to,t.title,t.status
                    FROM events e LEFT JOIN tasks t ON t.id=e.task_id
                    ORDER BY e.id DESC LIMIT 50
                """).fetchall()
            finally:
                connection.close()

        tasks_by_agent: dict[str, list[dict[str, Any]]] = {}
        for row in task_rows:
            if row["assigned_to"]:
                tasks_by_agent.setdefault(row["assigned_to"], []).append(dict(row))

        nodes = [{"id": "angela", "name": "Angela Executive Command Center", "department": "Executive",
                  "state": "HEALTHY", "activity": "IDLE", "queue": 0, "lastHeartbeat": None}]
        for agent in agents:
            name = agent.get("name", "Unknown Agent")
            if name == "Angela Executive Command Center":
                continue
            tasks = tasks_by_agent.get(name, [])
            recent = [
                t for t in tasks
                if (age := _age_seconds(t.get("updated_at"), now)) is not None and age <= ACTIVE_SECONDS
            ]
            active = next((t for t in recent if t["status"] in {"ASSIGNED", "WORKING"}), None)
            failure = next((t for t in tasks if t["status"] == "FAILED"), None)
            stale = next((t for t in tasks if t["status"] in {"ASSIGNED", "WORKING"}), None)
            failure_age = _age_seconds(failure.get("updated_at"), now) if failure else None
            if failure and failure_age is not None and failure_age <= 86400:
                state, activity = "CRITICAL", "FAILED"
            elif active:
                state, activity = "HEALTHY", "ACTIVE"
            elif stale:
                state, activity = "ATTENTION", "STALE_ASSIGNMENT"
            else:
                health = str(agent.get("health_status", "UNKNOWN")).upper()
                state, activity = ("HEALTHY" if health in {"HEALTHY", "ONLINE", "OK"} else "UNKNOWN"), "IDLE"
            nodes.append({
                "id": agent.get("agent_id", name), "name": name, "department": agent.get("department", "Unassigned"),
                "state": state, "activity": activity, "queue": sum(t["status"] in {"ASSIGNED", "WORKING"} for t in tasks),
                "lastHeartbeat": tasks[0]["updated_at"] if tasks else None,
                "currentMission": active["id"] if active else None,
            })

        events = []
        active_edges = []
        for row in event_rows:
            record = dict(row)
            age = _age_seconds(record["created_at"], now)
            event_type = record["event_type"].upper()
            target = record.get("assigned_to") or "Angela Executive Command Center"
            if event_type == "CREATED":
                source, target = "Founder", "Angela Executive Command Center"
            elif event_type == "ASSIGNED":
                source = "Angela Executive Command Center"
            else:
                source = target
            status = "CRITICAL" if event_type == "FAILED" else "SUCCESS" if event_type == "COMPLETED" else "RUNNING" if event_type in {"ASSIGNED", "PROGRESS"} else "RECORDED"
            event = {"eventId": record["id"], "timestamp": record["created_at"], "sourceAgent": source,
                     "targetAgent": target, "action": event_type, "missionId": record["task_id"],
                     "status": status, "latencyMs": None, "severity": "CRITICAL" if event_type == "FAILED" else "INFO",
                     "subsystem": "task_engine", "message": record.get("message"), "ageSeconds": age}
            events.append(event)
            if age is not None and age <= ACTIVE_SECONDS and event_type in {"ASSIGNED", "PROGRESS"}:
                active_edges.append(event)

        shared = self.bus.recent(50)
        implemented = {
            "Founder": ("SHAKTHI-FOUNDER", "Executive"),
            "Angela Executive Command Center": ("SHAKTHI-AGENT-ANGELLA", "Executive"),
            "SHAKTHI Prompt Architect": ("SHAKTHI-AGENT-PA", "Executive Intelligence"),
            "Policy / Security Gate": ("SHAKTHI-COMPONENT-POLICY", "Governance"),
            "Codex Engineering Agent": ("SHAKTHI-AGENT-CODEX", "Engineering"),
            "SHAKTHI Guardian": ("SHAKTHI-AGENT-GUARDIAN", "Security Operations"),
            "QA Agent": ("SHAKTHI-AGENT-QA", "Quality Assurance"),
            "Bug Fixer Agent": ("SHAKTHI-AGENT-BUGFIX", "Development / Reliability"),
        }
        existing_names = {node["name"] for node in nodes}
        for name, (node_id, department) in implemented.items():
            related = [event for event in shared if name in {event["source_agent"], event["target_agent"]}]
            last = related[0] if related else None
            age = _age_seconds(last["timestamp"], now) if last else None
            active = age is not None and age <= ACTIVE_SECONDS and last["status"] in {"RUNNING", "SUCCESS", "PENDING_APPROVAL", "BLOCKED", "FAILED"}
            if name not in existing_names:
                state = "CRITICAL" if last and last["status"] == "FAILED" else "ATTENTION" if last and last["status"] == "BLOCKED" else "HEALTHY" if active else "UNKNOWN"
                nodes.append({"id":node_id,"name":name,"department":department,"state":state,"activity":"ACTIVE" if active else "IDLE","queue":0,"lastHeartbeat":last["timestamp"] if last else None,"currentMission":last["mission_id"] if active else None})
        for record in shared:
            age = _age_seconds(record["timestamp"], now)
            event = {"eventId":record["event_id"],"timestamp":record["timestamp"],"sourceAgent":record["source_agent"],"targetAgent":record["target_agent"],"action":record["action"],"missionId":record["mission_id"],"taskId":record.get("task_id"),"status":record["status"],"latencyMs":record.get("latency_ms"),"severity":record["severity"],"subsystem":record["subsystem"],"message":record["message"],"repo":record["repo"],"dataSource":record["data_source"],"ageSeconds":age}
            events.append(event)
            if age is not None and age <= ACTIVE_SECONDS and record["status"] in {"RUNNING", "SUCCESS", "PENDING_APPROVAL", "BLOCKED", "FAILED"}:
                active_edges.append(event)
        events.sort(key=lambda event: event["timestamp"], reverse=True)

        return {"source": "SQLite task_engine.events", "generatedAt": now.isoformat(),
                "activeWindowSeconds": ACTIVE_SECONDS, "nodes": nodes,
                "activeEdges": active_edges, "events": events[:20],
                "degraded": not self.db_path.exists()}
