"""
SHAKTHI MARKETING — top-of-funnel content, wired into Sales, not standalone.

generate_content() reads real lead history (db.list_leads) before writing,
so "knows what messaging converts" is an actual query, not a claim. Every
variant lands in content_queue; send_to_sales() is the real hand-off --
it creates an actual routing.run_task("sales", ...) call, so marketing
output becoming sales input is a real `tasks` row, not just a status flag.

Same non-nested-connection rule as sales.py: every function opens, uses,
and closes its own db.get_conn() before calling anything else that touches
the database.
"""
import json
import re

from . import db, routing

_ICP_RE = re.compile(r"ICP_FIT:\s*([01]?\.?\d+)", re.IGNORECASE)

# Genuinely different angles, not three rewordings of the same sentence --
# the role_prompt already says this, enforced here by giving each variant
# call a distinct instruction rather than trusting the model to vary itself
# across three near-identical prompts.
ANGLES = ["pain-first (open with the problem/cost of inaction)",
          "outcome-first (open with the result/transformation)",
          "proof-first (open with evidence -- a number, a mechanism, a specific claim)"]


def _clamp01(raw):
    try:
        return max(0.0, min(1.0, float(raw)))
    except (TypeError, ValueError):
        return None


def _split_icp_fit(text: str):
    m = _ICP_RE.search(text)
    if not m:
        return text.strip(), None
    return text[:m.start()].strip(), _clamp01(m.group(1))


def generate_content(business_id, content_type: str, target: str, brief: str, count: int = 3) -> list:
    with db.get_conn() as conn:
        recent_leads = db.list_leads(conn, limit=20)
    converted = [l for l in recent_leads if l["status"] in ("contacted", "negotiating", "won")]
    context_note = f"{len(converted)} lead(s) already contacted/in-progress" if converted else "no lead history yet"

    angles = ANGLES[:count]
    results = []
    for i, angle in enumerate(angles):
        label = chr(65 + i)  # A, B, C
        goal = (
            f"Write ONE {content_type.replace('_', ' ')} for this offer. Angle: {angle}.\n\n"
            f"Offer/brief: {brief}\nTarget audience: {target}\nContext: {context_note}\n\n"
            "Write the content first. Then, on its own final line, write EXACTLY:\n"
            "ICP_FIT: <0.00-1.00, how well this targets our ideal customer profile>"
        )
        result = routing.run_task("marketing", goal, business_id=business_id)
        content_text, fit = _split_icp_fit(result["output"])

        with db.get_conn() as conn:
            content_id = db.insert_content(conn, business_id, content_type, label, target, content_text, fit)

        results.append({"content_id": content_id, "variant": label, "angle": angle,
                         "task_id": result["task_id"], "icp_fit": fit, "content": content_text})
    return results


def send_to_sales(content_id: int, lead_id: int = None) -> dict:
    """The real marketing -> sales wiring: this creates an actual sales-agent
    task (routing.run_task("sales", ...)), not just a status flag on the row."""
    with db.get_conn() as conn:
        content = db.get_content(conn, content_id)
    if not content:
        raise ValueError(f"no content #{content_id}")

    if lead_id is not None:
        with db.get_conn() as conn:
            lead = db.get_lead(conn, lead_id)
        if not lead:
            raise ValueError(f"no lead #{lead_id}")
        goal = (
            "Adapt this marketing draft into outreach for a specific lead. Keep the angle, "
            "personalize the specifics. Never invent pricing or commitments not given.\n\n"
            f"Lead: {lead['name']} ({lead['email']})\nNotes: {lead['notes'] or '(none)'}\n\n"
            f"Marketing draft ({content['content_type']}, variant {content['variant_label']}):\n{content['content']}"
        )
        business_id = lead["business_id"]
    else:
        goal = (
            f"This marketing draft ({content['content_type']}, variant {content['variant_label']}, "
            f"target: {content['target']}) is ready for outreach use. Confirm it's ready to send "
            "as-is, or note what to adjust first.\n\n" + content["content"]
        )
        business_id = content["business_id"]

    result = routing.run_task("sales", goal, business_id=business_id)

    with db.get_conn() as conn:
        db.update_content_status(conn, content_id, "sent_to_sales")
        if lead_id is not None:
            db.log_lead_event(conn, lead_id, "status_change",
                               json.dumps({"note": f"marketing content #{content_id} sent to sales"}),
                               task_id=result["task_id"])

    return {"content_id": content_id, "lead_id": lead_id, "task_id": result["task_id"],
            "status": result["status"], "output": result["output"]}
