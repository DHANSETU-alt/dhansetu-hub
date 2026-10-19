"""
Voice command history — reporting/formatting on top of the voice_commands
table voice.py already writes to. A real separate module, not a rename of
existing code: this is new capability (summary stats, formatted text for
Telegram/CLI, a denied-commands view for the Security angle) that didn't
exist before, unlike splitting voice.py's recording/STT/routing apart for
no functional gain.
"""
from . import db


def recent(limit: int = 20) -> list:
    with db.get_conn() as conn:
        return db.recent_voice_commands(conn, limit=limit)


def summary(limit: int = 100) -> dict:
    commands = recent(limit)
    by_identity = {}
    by_category = {}
    denied = []
    for c in commands:
        by_identity[c["identity"]] = by_identity.get(c["identity"], 0) + 1
        if c["routed_agent"]:
            by_category[c["routed_agent"]] = by_category.get(c["routed_agent"], 0) + 1
        if c["denied_reason"]:
            denied.append(c)
    return {
        "total": len(commands),
        "by_identity": by_identity,
        "by_category": by_category,
        "denied_count": len(denied),
        "denied": denied,
    }


def format_report(limit: int = 10) -> str:
    """Plain-text report for Telegram/CLI -- not a JSON dump."""
    commands = recent(limit)
    if not commands:
        return "No voice commands logged yet."

    s = summary(limit=100)
    lines = [
        f"*Voice Commander* — {s['total']} commands (last 100), {s['denied_count']} denied",
        "",
    ]
    for c in commands:
        marker = "DENIED" if c["denied_reason"] else "ok"
        lang = f" [{c['detected_language']}]" if c["detected_language"] else ""
        lines.append(f"  [{marker}] ({c['identity']}{lang}) \"{c['raw_transcript'][:60]}\" -> {c['routed_agent']}/{c['routed_action']}")
    return "\n".join(lines)
