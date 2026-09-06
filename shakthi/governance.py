"""Governance primitives shared by missions and execution systems."""

from __future__ import annotations

from enum import IntEnum, StrEnum


class AutonomyLevel(IntEnum):
    A0_OBSERVE = 0
    A1_RECOMMEND = 1
    A2_SAFE_INTERNAL = 2
    A3_REVERSIBLE_OPERATIONAL = 3
    A4_PREAPPROVED_WORKFLOW = 4
    A5_STRATEGIC_POLICY = 5


class TruthState(StrEnum):
    PLANNED = "PLANNED"
    CODED = "CODED"
    LOCALLY_TESTED = "LOCALLY_TESTED"
    STAGING_VERIFIED = "STAGING_VERIFIED"
    EXTERNAL_VERIFICATION_REQUIRED = "EXTERNAL_VERIFICATION_REQUIRED"
    PRODUCTION_VERIFIED = "PRODUCTION_VERIFIED"


class GovernanceError(ValueError):
    pass


def requires_founder_approval(*, autonomy: AutonomyLevel, risk: str, production_change: bool) -> bool:
    """Conservative default: high-impact or strategic production actions are gated."""
    return production_change or autonomy >= AutonomyLevel.A4_PREAPPROVED_WORKFLOW or risk.upper() in {"HIGH", "CRITICAL"}


def assert_execution_allowed(
    *, autonomy: AutonomyLevel, risk: str, production_change: bool, approved: bool
) -> None:
    if requires_founder_approval(autonomy=autonomy, risk=risk, production_change=production_change) and not approved:
        raise GovernanceError("Founder approval is required by policy")


def next_confidence_action(score: int) -> str:
    if not 0 <= score <= 100:
        raise ValueError("confidence must be between 0 and 100")
    if score >= 90:
        return "CONTROLLED_EXECUTION"
    if score >= 75:
        return "ADDITIONAL_VERIFICATION"
    if score >= 50:
        return "SPECIALIST_REVIEW_REQUIRED"
    return "DO_NOT_AUTONOMOUSLY_EXECUTE"

