import sqlite3
from pathlib import Path

import pytest

from orchestrator import config, db, personal_plane


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    path = tmp_path / "personal.db"
    monkeypatch.setattr(config, "DB_PATH", path)
    db.init_db()
    return path


def test_goal_task_and_completion_round_trip(isolated_db):
    goal = personal_plane.create_goal("Launch Jarvis mode", "owner", "Owner")
    task = personal_plane.create_task("Define wake word", goal["id"], "owner", "Owner")

    assert personal_plane.list_goals("owner")[0]["title"] == "Launch Jarvis mode"
    assert personal_plane.list_tasks("owner")[0]["status"] == "pending"
    completed = personal_plane.complete_task(task["id"], "owner", "Owner")
    assert completed["status"] == "completed"


def test_reminder_due_filter_and_idempotency(isolated_db):
    reminder = personal_plane.create_reminder(
        "Review priorities", "2020-01-01T09:00:00+00:00", "owner", "Owner", request_id="req-1"
    )
    same = personal_plane.create_reminder(
        "Review priorities", "2020-01-01T09:00:00+00:00", "owner", "Owner", request_id="req-1"
    )
    assert same["id"] == reminder["id"]
    assert personal_plane.list_due_reminders("owner", "2020-01-02T00:00:00+00:00")[0]["id"] == reminder["id"]


def test_guest_cannot_create_owner_only_goal(isolated_db):
    with pytest.raises(PermissionError):
        personal_plane.create_goal("Private goal", "guest", "Guest")


def test_invalid_input_is_rejected(isolated_db):
    with pytest.raises(ValueError, match="title"):
        personal_plane.create_task("", None, "owner", "Owner")
