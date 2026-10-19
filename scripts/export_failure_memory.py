#!/usr/bin/env python3
"""Generate data/failure-memory.json from the real bugs + failure_analyses
tables. Read-only against shakthi.db -- this file is a generated export,
never a hand-maintained parallel store (see
docs/v3.4/FAILURE_MEMORY_AND_BUGFIX_SYSTEM.md). Re-run this after real
bugs/analyses change; don't edit the JSON output by hand.

Usage: python3 scripts/export_failure_memory.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from orchestrator import db  # noqa: E402

OUT_PATH = ROOT / "data" / "failure-memory.json"


def export():
    with db.get_conn() as conn:
        bugs = [dict(r) for r in conn.execute("SELECT * FROM bugs ORDER BY id").fetchall()]
        analyses = [dict(r) for r in conn.execute(
            "SELECT * FROM failure_analyses WHERE source_type = 'bug' ORDER BY id"
        ).fetchall()]

    analyses_by_bug_id = {}
    for a in analyses:
        analyses_by_bug_id.setdefault(a["source_id"], []).append(a)

    entries = []
    for bug in bugs:
        matched = analyses_by_bug_id.get(bug["id"], [])
        # A bug can have more than one linked failure_analyses row over
        # time (e.g. it regressed and got re-analyzed) -- take the most
        # recent as the current prevention_rule/regression_check, but
        # don't silently drop the earlier ones from the record.
        latest = matched[-1] if matched else None
        entries.append({
            "failure_id": f"bug-{bug['id']}",
            "date": bug["created_at"],
            "agent": latest["agent_id"] if latest else None,
            "task_id": bug["related_task_id"],
            "symptom": bug["description"],
            "root_cause": bug["root_cause"],
            "fix_applied": bug["fix_recommendation"] if bug["applied_at"] else None,
            "files_changed": [bug["file_path"]] if bug["file_path"] else [],
            "prevention_rule": latest["preventive_action"] if latest else None,
            "regression_check": {
                "regression_count": bug["regression_count"],
                "occurrence_count": bug["occurrence_count"],
                "duplicate_of": bug["duplicate_of"],
            },
            "status": bug["status"],
            "_source": "bugs",
            "_linked_failure_analyses_ids": [a["id"] for a in matched],
        })

    # failure_analyses rows with no matching bug (source_type != 'bug',
    # e.g. task_failure/incident/manual) are real failure memory too --
    # include them as their own entries rather than silently dropping them.
    with db.get_conn() as conn:
        other = [dict(r) for r in conn.execute(
            "SELECT * FROM failure_analyses WHERE source_type != 'bug' ORDER BY id"
        ).fetchall()]
    for a in other:
        entries.append({
            "failure_id": f"analysis-{a['id']}",
            "date": a["created_at"],
            "agent": a["agent_id"],
            "task_id": a["source_id"] if a["source_type"] == "task_failure" else None,
            "symptom": a["summary"],
            "root_cause": a["root_cause"],
            "fix_applied": a["corrective_action"],
            "files_changed": [],
            "prevention_rule": a["preventive_action"],
            "regression_check": None,
            "status": a["status"],
            "_source": a["source_type"],
            "_linked_failure_analyses_ids": [a["id"]],
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "generated_by": "scripts/export_failure_memory.py",
        "count": len(entries),
        "entries": entries,
    }, indent=2))
    print(f"Wrote {len(entries)} failure-memory entries to {OUT_PATH}")


if __name__ == "__main__":
    export()
