"""
Founder-facing high-level work tracker -- "Task 1", "Task 2", ... Distinct
from routing.py's `tasks` table (one row per agent call, internal
plumbing); an initiative is a standing piece of real work the founder
asked for, shown on the dashboard with a real percent-complete computed
from its own milestones -- never a hand-picked number.
"""
from . import db


def add_initiative(title: str, artifact_url: str = None) -> dict:
    with db.get_conn() as conn:
        initiative_id = db.insert_initiative(conn, title, artifact_url)
        return _get(conn, initiative_id)


def add_milestone(initiative_id: int, title: str, done: bool = False) -> dict:
    with db.get_conn() as conn:
        db.add_initiative_milestone(conn, initiative_id, title, done=done)
        return _get(conn, initiative_id)


def mark_milestone(milestone_id: int, done: bool = True) -> None:
    with db.get_conn() as conn:
        db.set_milestone_done(conn, milestone_id, done=done)


def set_status(initiative_id: int, status: str) -> dict:
    if status not in ("running", "paused", "done"):
        raise ValueError(f"invalid status {status!r} -- must be running|paused|done")
    with db.get_conn() as conn:
        db.set_initiative_status(conn, initiative_id, status)
        return _get(conn, initiative_id)


def list_all(status: str = None) -> list:
    with db.get_conn() as conn:
        return db.list_initiatives(conn, status=status)


def _get(conn, initiative_id: int) -> dict:
    rows = db.list_initiatives(conn)
    for r in rows:
        if r["id"] == initiative_id:
            return r
    raise ValueError(f"no initiative with id {initiative_id}")
