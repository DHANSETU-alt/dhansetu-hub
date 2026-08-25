"""
ERT -- postmortems and audit trail. Every field in the postmortem that
CAN be pulled directly from real data is (timeline, timestamps, owner,
severity, root cause, fix) -- only the narrative sections (Lessons
Learned, Future Recommendations) are model-generated, and even those are
grounded in the real timeline/root_cause/fix passed into the prompt, not
invented from nothing. Falls back to a deterministic templated version if
the model call fails -- a postmortem must exist even if the model doesn't.

One file per incident (postmortems/{incident_number}_postmortem.md) --
not a single POSTMORTEM_REPORT.md overwritten every time, which would
destroy history the moment a second incident closed. Named for the
incident it documents, same reasoning as everywhere else in this project
that a shared filename can't represent multiple runs.
"""
from datetime import datetime

from . import config, db

config.POSTMORTEMS_DIR.mkdir(exist_ok=True)


def _duration_str(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"


def audit_trail(incident_id: int) -> list:
    with db.get_conn() as conn:
        return db.incident_events(conn, incident_id)


def _ai_narrative(incident: dict, events: list) -> dict:
    """Model-generated Lessons Learned / Future Recommendations / Mistakes
    Made, grounded in the real incident record. Returns a dict with those
    three keys; on any failure, returns honest placeholder text instead
    of crashing the postmortem."""
    from . import bug_fixer

    timeline_text = "\n".join(f"- {e['created_at']}: [{e['event_type']}] {e['detail']}" for e in events)
    prompt = (
        "IMPORTANT: this is NOT a decision to score. Ignore any json decision-block format. "
        "Write plain prose only, under the three headings exactly as given below.\n\n"
        f"Incident {incident['incident_number']} ({incident['incident_type']}, severity {incident['severity']}):\n"
        f"{incident['description']}\n\n"
        f"Root cause: {incident['root_cause'] or 'not recorded'}\n"
        f"Fix applied: {incident['fix_applied'] or 'not recorded'}\n\n"
        f"Timeline:\n{timeline_text}\n\n"
        "Write:\nMISTAKES MADE:\n<2-3 sentences>\n\nLESSONS LEARNED:\n<2-3 sentences>\n\n"
        "FUTURE RECOMMENDATIONS:\n<2-3 sentences>"
    )
    try:
        with db.get_conn() as conn:
            task_id = bug_fixer.new_pipeline_task(conn, f"Postmortem narrative for {incident['incident_number']}")
            text = bug_fixer.call_agent(conn, task_id, "ceo", prompt)
        sections = {"mistakes_made": "", "lessons_learned": "", "future_recommendations": ""}
        current = None
        for line in text.splitlines():
            u = line.strip().upper()
            if u.startswith("MISTAKES MADE"):
                current = "mistakes_made"; continue
            if u.startswith("LESSONS LEARNED"):
                current = "lessons_learned"; continue
            if u.startswith("FUTURE RECOMMENDATIONS"):
                current = "future_recommendations"; continue
            if current and line.strip():
                sections[current] += line.strip() + " "
        if not any(sections.values()):
            raise ValueError("model reply didn't contain any of the expected headings")
        return {k: v.strip() or "(not generated)" for k, v in sections.items()}
    except Exception as e:
        placeholder = f"(AI narrative unavailable: {e}. Fill in manually.)"
        return {"mistakes_made": placeholder, "lessons_learned": placeholder, "future_recommendations": placeholder}


def generate_postmortem(incident_id: int, use_ai: bool = True) -> str:
    with db.get_conn() as conn:
        incident = db.get_incident(conn, incident_id=incident_id)
        if not incident:
            raise ValueError(f"no such incident id: {incident_id}")
        events = db.incident_events(conn, incident_id)

    detection_time = incident["created_at"]
    response_time = next((e["created_at"] for e in events if e["event_type"] == "state_change" and "ACKNOWLEDGED" in (e["detail"] or "")), None)
    resolution_time = incident.get("resolved_at")

    response_seconds = None
    if response_time:
        response_seconds = (datetime.strptime(response_time, "%Y-%m-%d %H:%M:%S") -
                             datetime.strptime(detection_time, "%Y-%m-%d %H:%M:%S")).total_seconds()
    resolution_seconds = None
    if resolution_time:
        resolution_seconds = (datetime.strptime(resolution_time, "%Y-%m-%d %H:%M:%S") -
                               datetime.strptime(detection_time, "%Y-%m-%d %H:%M:%S")).total_seconds()

    narrative = _ai_narrative(incident, events) if use_ai else {
        "mistakes_made": "(AI narrative skipped)", "lessons_learned": "(AI narrative skipped)", "future_recommendations": "(AI narrative skipped)"
    }

    timeline_lines = "\n".join(f"- {e['created_at']} — **{e['event_type']}**: {e['detail']}" for e in events)

    content = f"""# Postmortem — {incident['incident_number']}

**Title:** {incident['incident_type'].replace('_', ' ').title()}
**Date:** {incident['created_at']}
**Severity:** {incident['severity']}
**Owner:** {incident['owner']}
**Support Team:** {", ".join(json_loads_safe(incident['support_team']))}
**Detected by:** {incident['detected_by']}

## Timeline

{timeline_lines or "(no events recorded)"}

## Timing

- Detection: {detection_time}
- Response time: {_duration_str(response_seconds)}
- Resolution time: {_duration_str(resolution_seconds)}

## Root Cause

{incident['root_cause'] or "(not recorded)"}

## Systems Affected

{incident['incident_type']}

## Actions Taken / Fix Applied

{incident['fix_applied'] or "(not recorded)"}

{f"**Recovery action:** {incident['recovery_action']} — {incident['recovery_result']}" if incident.get('recovery_action') else ""}

## Mistakes Made

{narrative['mistakes_made']}

## Lessons Learned

{narrative['lessons_learned']}

## Preventive Actions / Future Recommendations

{narrative['future_recommendations']}
"""

    out_path = config.POSTMORTEMS_DIR / f"{incident['incident_number']}_postmortem.md"
    out_path.write_text(content)
    return str(out_path)


def json_loads_safe(text: str) -> list:
    import json
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []
