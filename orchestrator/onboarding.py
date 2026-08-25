"""
BLACKBOXOPS_OS AI EMPLOYEE ONBOARDING -- Stage 1 (Business Discovery) only.

The founder's own spec runs to 9 stages (generate 12 AI employee types,
KPI dashboards, Microsoft-tools automation, a knowledge base, recurring
reporting). Deliberately scoped to Stage 1 for now, per an explicit
decision -- collect the real intake, identify real bottlenecks in 5
categories, present the findings. Stages 2-9 are not started; building
them silently ahead of a decision on Stage 1 would be the wrong call.

INTAKE_FIELDS is the single source of truth for what Stage 1 collects --
the CLI, the API route, and the form all read from it, so adding a field
later is one change, not four.
"""
from . import db, routing

INTAKE_FIELDS = [
    ("business_name", "Business Name", True),
    ("industry", "Industry", False),
    ("website", "Website", False),
    ("business_model", "Business Model", False),
    ("target_customer", "Target Customer", False),
    ("revenue_streams", "Primary Revenue Streams", False),
    ("team_size", "Current Team Size", False),
    ("monthly_revenue_range", "Monthly Revenue Range", False),
    ("main_challenges", "Main Business Challenges", False),
    ("preferred_tools", "Preferred Tools", False),
    ("current_software", "Current Software", False),
    ("growth_goal_12mo", "Growth Goal (Next 12 Months)", False),
]

_CATEGORY_MARKERS = ["REVENUE:", "OPERATIONAL:", "MARKETING:", "SALES:", "SUPPORT:"]


def start_discovery(fields: dict) -> int:
    if not fields.get("business_name"):
        raise ValueError("business_name is required")
    with db.get_conn() as conn:
        return db.insert_business_discovery(conn, fields)


def _parse_bottlenecks(text: str) -> dict:
    """Splits on the five fixed section markers. Fail-closed like every
    other parser in this project: a section that isn't found comes back
    None, never a fabricated finding."""
    positions = []
    for marker in _CATEGORY_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            positions.append((idx, marker))
    positions.sort()

    result = {m.rstrip(":").lower(): None for m in _CATEGORY_MARKERS}
    for i, (idx, marker) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        content = text[idx + len(marker):end].strip()
        result[marker.rstrip(":").lower()] = content or None
    return result


def analyze_discovery(discovery_id: int) -> dict:
    with db.get_conn() as conn:
        discovery = db.get_business_discovery(conn, discovery_id)
    if not discovery:
        raise ValueError(f"no discovery #{discovery_id}")

    lines = [f"{label}: {discovery.get(key) or '(not provided)'}" for key, label, _req in INTAKE_FIELDS]
    goal = "New business intake for onboarding analysis:\n\n" + "\n".join(lines)

    result = routing.run_task("business_analyst", goal, business_id=None)
    bottlenecks = _parse_bottlenecks(result["output"])

    with db.get_conn() as conn:
        db.update_business_discovery(
            conn, discovery_id, status="analyzed", task_id=result["task_id"],
            revenue_bottlenecks=bottlenecks["revenue"], operational_bottlenecks=bottlenecks["operational"],
            marketing_bottlenecks=bottlenecks["marketing"], sales_bottlenecks=bottlenecks["sales"],
            support_bottlenecks=bottlenecks["support"],
        )
        updated = db.get_business_discovery(conn, discovery_id)

    return updated
