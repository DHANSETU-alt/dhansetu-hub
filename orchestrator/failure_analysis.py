"""
Failure Analysis Engine -- Task 4, scoped down from the founder's full
"ANGELLA OMEGA" Six Sigma/DMAIC spec by a real CEO decision (decisions#11:
the whole framework is too large to build at once; build one high-leverage
process first -- root-cause analysis for a real recurring failure).

This is deliberately a record-and-query layer, not an auto-generating one.
The 5-Whys/root-cause/corrective/preventive fields need real investigation
to be worth anything -- an unvalidated local model free-generating "root
causes" would repeat this project's own NO_MEMORY_CONTEXT lesson (see
routing.py) in a new form. Entries are written by whoever actually did the
investigation (so far: me, by hand, grounded in real bugs already fixed
this session) and recorded here so they're queryable instead of living
only in conversation history.
"""
from . import db


def record_analysis(source_type: str, source_id, title: str, severity: str, summary: str,
                     five_whys: list, root_cause: str, corrective_action: str,
                     preventive_action: str, lessons_learned: str, status: str = "open") -> int:
    with db.get_conn() as conn:
        return db.insert_failure_analysis(
            conn, source_type, source_id, title, severity, summary, five_whys,
            root_cause, corrective_action, preventive_action, lessons_learned, status,
        )


def list_analyses(status: str = None) -> list:
    with db.get_conn() as conn:
        return db.list_failure_analyses(conn, status=status)
