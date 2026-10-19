"""
SHAKTHI BUDDY — Phase v4. Family assistant, Gujarati/Hindi/English mixed.

Safe Mode is a real deterministic filter, not just a prompt instruction --
prompting alone is not a safety boundary for a child-facing feature, the
same reasoning that put deterministic checks in security.py and
bug_fixer's patch scanner rather than trusting a local model's judgment
alone. Honest limitation: the blocklist is strongest for English terms;
it will not catch everything in Gujarati/Hindi transliteration. It is a
defense-in-depth layer alongside the role_prompt's own instructions, not a
complete guarantee -- an adult should still supervise Child Mode use.
"""
import re

from . import bug_fixer, db

MODES = ("child", "general", "family")

# Deliberately blunt, English-centric keyword categories. Not exhaustive --
# see module docstring.
UNSAFE_PATTERNS = {
    "violence": re.compile(r"\b(kill|murder|suicide|self.?harm|weapon|gun|knife.attack)\b", re.IGNORECASE),
    "adult_content": re.compile(r"\b(sex|porn|nude|explicit)\b", re.IGNORECASE),
    "substances": re.compile(r"\b(drug|cocaine|heroin|overdose|get drunk)\b", re.IGNORECASE),
    "dangerous_advice": re.compile(r"\b(how to make a bomb|hack into|steal)\b", re.IGNORECASE),
}


def check_safe(text: str) -> str:
    """Returns the matched category name if text trips a filter, else None."""
    for category, pattern in UNSAFE_PATTERNS.items():
        if pattern.search(text):
            return category
    return None


CHILD_SAFE_REDIRECT = (
    "That's a grown-up topic — let's ask a parent about that one. "
    "Want to hear a story or try a fun science question instead?"
)


def chat(session_id: str, mode: str, message: str) -> dict:
    if mode not in MODES:
        mode = "general"

    if mode == "child":
        blocked = check_safe(message)
        if blocked:
            with db.get_conn() as conn:
                db.log_buddy_message(conn, session_id, mode, message, response=CHILD_SAFE_REDIRECT, blocked_reason=blocked)
            return {"response": CHILD_SAFE_REDIRECT, "blocked": True, "blocked_reason": blocked}

    with db.get_conn() as conn:
        history = db.buddy_history(conn, session_id, limit=6)
        history_text = "\n".join(f"{'Buddy' if h['response'] else 'Them'}: {h['response'] or h['message']}" for h in history)
        task_id = bug_fixer.new_pipeline_task(conn, f"Buddy chat ({mode})")
        prompt = f"Mode: {mode}\n\nRecent conversation:\n{history_text}\n\nThem: {message}"
        response = bug_fixer.call_agent(conn, task_id, "buddy", prompt)
        db.update_task(conn, task_id, "done", response)

    if mode == "child":
        output_blocked = check_safe(response)
        if output_blocked:
            # Defense in depth: even a clean input can produce an unsafe
            # response from a small local model. Never send it.
            with db.get_conn() as conn:
                db.log_buddy_message(conn, session_id, mode, message, response=CHILD_SAFE_REDIRECT,
                                      blocked_reason=f"output:{output_blocked}")
            return {"response": CHILD_SAFE_REDIRECT, "blocked": True, "blocked_reason": f"output:{output_blocked}"}

    with db.get_conn() as conn:
        db.log_buddy_message(conn, session_id, mode, message, response=response)
    return {"response": response, "blocked": False}
