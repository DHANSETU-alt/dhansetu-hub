"""Kaixen continuous error triage.

Kaixen observes real task/error records and creates traceable bug tickets. It
does not diagnose with invented context or apply patches. Existing Bug Fixer
gates own analysis, staging, QA, security, CEO review and confirmed apply.
"""
from __future__ import annotations

import json
import time

from . import bug_fixer, db


def triage_once() -> dict:
    candidates = bug_fixer.scan_for_bugs()
    created = []
    linked = []
    with db.get_conn() as conn:
        existing_by_title = {row["title"]: row["id"] for row in db.list_bugs(conn, limit=1000)}
    groups = {}
    for candidate in candidates:
        key = (candidate["source"], candidate["title"])
        groups.setdefault(key, []).append(candidate)

    for grouped in groups.values():
        candidate = grouped[0]
        existing_id = existing_by_title.get(candidate["title"])
        if existing_id:
            with db.get_conn() as conn:
                linked_count = 0
                for occurrence in grouped:
                    if occurrence.get("related_error_id"):
                        db.mark_error_triaged(conn, occurrence["related_error_id"], existing_id)
                        db.increment_occurrence(conn, existing_id)
                        linked_count += 1
                if linked_count:
                    db.log_bug_event(
                        conn, existing_id, "recurred",
                        f"Kaixen linked {linked_count} additional matching error occurrence(s).",
                    )
            linked.append({"bug_id": existing_id, "occurrences": len(grouped), **candidate})
            continue
        with db.get_conn() as conn:
            description = bug_fixer._describe_candidate(conn, candidate)
            if len(grouped) > 1:
                description += f"\n\nKaixen grouped {len(grouped)} matching occurrences in this triage cycle."
            severity = "P1" if candidate["source"] == "task_failure" else "P2"
            bug_id = db.insert_bug(
                conn,
                candidate["title"],
                description,
                severity=severity,
                source=f"kaixen:{candidate['source']}",
                related_task_id=candidate.get("related_task_id"),
                related_error_id=candidate.get("related_error_id"),
            )
            for occurrence in grouped:
                if occurrence.get("related_error_id"):
                    db.mark_error_triaged(conn, occurrence["related_error_id"], bug_id)
            db.log_bug_event(conn, bug_id, "detected", json.dumps({"observer": "kaixen_bot", **candidate}))
        created.append({"bug_id": bug_id, "occurrences": len(grouped), **candidate})
    return {"candidates": len(candidates), "groups": len(groups), "created": created, "linked": linked}


def run_loop(interval_seconds: int = 30) -> None:
    interval_seconds = max(10, int(interval_seconds))
    print(f"Kaixen Bot online: real error triage every {interval_seconds}s", flush=True)
    while True:
        try:
            result = triage_once()
            if result["created"]:
                print(json.dumps(result, default=str), flush=True)
        except Exception as exc:
            # Never let the observer silently die; best-effort logging must not
            # mask the original failure or recursively crash the loop.
            try:
                with db.get_conn() as conn:
                    db.log_error(conn, "kaixen_bot", "triage_once", str(exc), "")
            except Exception:
                pass
            print(f"Kaixen triage error: {exc}", flush=True)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_loop()
