"""Angela mission creation and persistence."""

from __future__ import annotations

from .governance import AutonomyLevel
from .missions import Confidence, Mission


def draft_mission(command: str, *, project: str = "Unassigned") -> Mission:
    """Create a conservative deterministic draft; evidence-backed enrichment follows later."""
    text = command.strip()
    if not text:
        raise ValueError("Founder command cannot be empty")
    lowered = text.lower()
    payment = any(word in lowered for word in ("payment", "payu", "razorpay", "refund"))
    production = any(word in lowered for word in ("production", "deploy", "live"))
    department = "PaymentOps" if payment else "Software Factory" if any(
        word in lowered for word in ("build", "android", "ios", "mac", "windows", "linux", "app")
    ) else "Mission Control"
    risk = "HIGH" if payment or production else "MEDIUM"
    autonomy = AutonomyLevel.A1_RECOMMEND if risk == "HIGH" else AutonomyLevel.A2_SAFE_INTERNAL
    agents = ["Thinker", "Planner", "Critic", "Judge"]
    if department == "PaymentOps":
        agents.extend(["PaymentOps Engineer", "Payment Certification Agent"])
    elif department == "Software Factory":
        agents.extend(["Architect", "Engineering Swarm", "QA Agent", "Security Agent"])
    # These scores explicitly reflect intake completeness, not correctness of an unexecuted plan.
    confidence = Confidence(decision=55, evidence=25, security=65, execution=50, business=45)
    return Mission(
        objective=text, business_impact="TO_BE_ASSESSED", priority="HIGH" if risk == "HIGH" else "NORMAL",
        project=project, department=department, agents=agents,
        budget={"currency": "INR", "limit": "FOUNDER_INPUT_REQUIRED"},
        estimated_compute_cost={"currency": "INR", "estimate": "PENDING_PLAN"},
        dependencies=[], risk=risk, security_classification="CONFIDENTIAL" if payment else "INTERNAL",
        autonomy_level=autonomy, rollback_plan="Required before any state-changing execution",
        testing_requirements=["Static analysis", "Unit tests", "Integration tests", "Security review"],
        success_criteria=["Objective-specific acceptance criteria approved", "Evidence recorded", "No critical findings"],
        confidence=confidence,
    )

