"""
DAILY TEAM WORK REGISTER — attendance, hours, and work assigned/done for
the real human team (expert engineers/staff — not AI agents, not manual
wage labor; that was the founder's own example when scoping this, not the
real composition of the team). Deliberately NOT wages/pay -- the founder
scoped this explicitly (work assigned/done, attendance, hours only), so no
rate/amount field exists here. Deterministic Python and SQL throughout --
there is no judgment call in "was this person present," so no model call
belongs in this module, unlike sales.py/marketing.py.

Distinct from orchestrator/worker_pool.py's `workers` table -- that's AI
thread pools (rapid/engineering/infra), this is real people. Same English
word, unrelated concept; don't conflate them.
"""
from . import db


def add_worker(business_id, name: str, role: str = None, contact: str = None) -> int:
    with db.get_conn() as conn:
        return db.insert_team_member(conn, business_id, name, role, contact)


def list_workers(business_id=None, status: str = None) -> list:
    with db.get_conn() as conn:
        return db.list_team_members(conn, business_id=business_id, status=status)


def log_day(worker_id: int, work_date: str, present: bool = True, hours_worked: float = None,
            work_assigned: str = None, work_done: str = None, notes: str = None) -> dict:
    with db.get_conn() as conn:
        worker = db.get_team_member(conn, worker_id)
    if not worker:
        raise ValueError(f"no worker #{worker_id}")

    with db.get_conn() as conn:
        db.upsert_daily_work_log(conn, worker_id, worker["business_id"], work_date, present,
                                  hours_worked, work_assigned, work_done, notes)
        entry = db.get_daily_work_log(conn, worker_id, work_date)
    return entry


def get_day(worker_id: int, work_date: str):
    with db.get_conn() as conn:
        return db.get_daily_work_log(conn, worker_id, work_date)


def worker_history(worker_id: int, date_from: str = None, date_to: str = None) -> list:
    with db.get_conn() as conn:
        return db.list_daily_work_logs(conn, worker_id=worker_id, date_from=date_from, date_to=date_to)


def daily_summary(work_date: str, business_id=None) -> dict:
    """The single-day 'who worked today' view -- a real daily standup/work
    log across the team."""
    with db.get_conn() as conn:
        entries = db.list_daily_work_logs(conn, business_id=business_id, work_date=work_date)
        workers = {w["id"]: w for w in db.list_team_members(conn, business_id=business_id)}

    present = [e for e in entries if e["present"]]
    absent = [e for e in entries if not e["present"]]
    total_hours = sum(e["hours_worked"] or 0 for e in present)
    logged_ids = {e["worker_id"] for e in entries}
    not_logged = [w for wid, w in workers.items() if wid not in logged_ids]

    return {
        "date": work_date,
        "present_count": len(present),
        "absent_count": len(absent),
        "total_hours": total_hours,
        "entries": entries,
        "not_logged": not_logged,  # active team members with no entry at all for this date -- a real gap, surfaced, not hidden
    }


def worker_summary(worker_id: int, date_from: str = None, date_to: str = None) -> dict:
    """Attendance-rate rollup for one team member over a range -- for
    review purposes only, still no pay math (out of scope per the founder)."""
    with db.get_conn() as conn:
        worker = db.get_team_member(conn, worker_id)
    if not worker:
        raise ValueError(f"no worker #{worker_id}")

    entries = worker_history(worker_id, date_from, date_to)
    present_days = [e for e in entries if e["present"]]
    total_hours = sum(e["hours_worked"] or 0 for e in present_days)

    return {
        "worker": worker,
        "days_logged": len(entries),
        "days_present": len(present_days),
        "days_absent": len(entries) - len(present_days),
        "total_hours": total_hours,
        "entries": entries,
    }
