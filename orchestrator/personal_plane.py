"""Shared personal goals, tasks, and reminders for voice and dashboard clients."""

from datetime import datetime

from .db import get_conn


def _require_title(title: str) -> str:
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title is required")
    return title.strip()


def _require_owner_role(role: str) -> None:
    if role not in {"Owner", "Family"}:
        raise PermissionError("this personal action requires Owner or Family access")


def _validate_timestamp(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("due_at must be an ISO timestamp")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("due_at must be an ISO timestamp") from exc
    return value


def _row(row):
    return dict(row) if row else None


def create_goal(title: str, actor_id: str, actor_role: str, request_id: str | None = None) -> dict:
    title = _require_title(title)
    _require_owner_role(actor_role)
    with get_conn() as conn:
        if request_id:
            existing = conn.execute("SELECT * FROM personal_goals WHERE request_id = ?", (request_id,)).fetchone()
            if existing:
                return dict(existing)
        cur = conn.execute(
            "INSERT INTO personal_goals(title, owner_id, status, request_id) VALUES (?, ?, 'active', ?)",
            (title, actor_id, request_id),
        )
        goal = conn.execute("SELECT * FROM personal_goals WHERE id = ?", (cur.lastrowid,)).fetchone()
        conn.execute("INSERT INTO personal_audit_events(actor_id, actor_role, action, object_type, object_id) VALUES (?, ?, 'create', 'goal', ?)", (actor_id, actor_role, cur.lastrowid))
        return dict(goal)


def list_goals(owner_id: str) -> list[dict]:
    with get_conn() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM personal_goals WHERE owner_id = ? ORDER BY created_at DESC", (owner_id,))]


def create_task(title: str, goal_id: int | None, actor_id: str, actor_role: str, request_id: str | None = None) -> dict:
    title = _require_title(title)
    _require_owner_role(actor_role)
    with get_conn() as conn:
        if request_id:
            existing = conn.execute("SELECT * FROM personal_tasks WHERE request_id = ?", (request_id,)).fetchone()
            if existing:
                return dict(existing)
        cur = conn.execute("INSERT INTO personal_tasks(title, goal_id, owner_id, status, request_id) VALUES (?, ?, ?, 'pending', ?)", (title, goal_id, actor_id, request_id))
        row = conn.execute("SELECT * FROM personal_tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
        conn.execute("INSERT INTO personal_audit_events(actor_id, actor_role, action, object_type, object_id) VALUES (?, ?, 'create', 'task', ?)", (actor_id, actor_role, cur.lastrowid))
        return dict(row)


def list_tasks(owner_id: str, status: str | None = None) -> list[dict]:
    with get_conn() as conn:
        if status:
            rows = conn.execute("SELECT * FROM personal_tasks WHERE owner_id = ? AND status = ? ORDER BY created_at DESC", (owner_id, status))
        else:
            rows = conn.execute("SELECT * FROM personal_tasks WHERE owner_id = ? ORDER BY created_at DESC", (owner_id,))
        return [dict(row) for row in rows]


def complete_task(task_id: int, actor_id: str, actor_role: str) -> dict:
    _require_owner_role(actor_role)
    with get_conn() as conn:
        cur = conn.execute("UPDATE personal_tasks SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ? AND owner_id = ?", (task_id, actor_id))
        if cur.rowcount == 0:
            raise ValueError("task not found")
        conn.execute("INSERT INTO personal_audit_events(actor_id, actor_role, action, object_type, object_id) VALUES (?, ?, 'complete', 'task', ?)", (actor_id, actor_role, task_id))
        return dict(conn.execute("SELECT * FROM personal_tasks WHERE id = ?", (task_id,)).fetchone())


def create_reminder(title: str, due_at: str, actor_id: str, actor_role: str, request_id: str | None = None) -> dict:
    title = _require_title(title)
    due_at = _validate_timestamp(due_at)
    _require_owner_role(actor_role)
    with get_conn() as conn:
        if request_id:
            existing = conn.execute("SELECT * FROM personal_reminders WHERE request_id = ?", (request_id,)).fetchone()
            if existing:
                return dict(existing)
        cur = conn.execute("INSERT INTO personal_reminders(title, due_at, owner_id, status, request_id) VALUES (?, ?, ?, 'pending', ?)", (title, due_at, actor_id, request_id))
        row = conn.execute("SELECT * FROM personal_reminders WHERE id = ?", (cur.lastrowid,)).fetchone()
        conn.execute("INSERT INTO personal_audit_events(actor_id, actor_role, action, object_type, object_id) VALUES (?, ?, 'create', 'reminder', ?)", (actor_id, actor_role, cur.lastrowid))
        return dict(row)


def list_due_reminders(owner_id: str, through: str) -> list[dict]:
    through = _validate_timestamp(through)
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM personal_reminders WHERE owner_id = ? AND status = 'pending' AND due_at <= ? ORDER BY due_at", (owner_id, through))
        return [dict(row) for row in rows]
