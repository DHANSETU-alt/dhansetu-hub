"""
SHAKTHI Worker Pool -- registry of worker types and what they run.

Workers are config, not new agents -- same "agents are config, not code"
philosophy as agents/*.yaml, but registered in the `workers` table, NOT
the `agents` table: workers do not make business decisions (no
role_prompt, no model call of their own, no allowed_tools) -- they only
execute an already-built function from an existing module and report the
result. Mixing them into `agents` would misrepresent them as
decision-makers, which the mission brief explicitly rules out.

Three types, matched to what they actually run:
  - rapid        fast, cheap, mostly-deterministic work (an HTTP-only
                  website audit, a finance calculation) -- high
                  concurrency, nothing here blocks for long.
  - engineering   heavier work involving a model call and/or a real
                  browser subprocess (chrome_developer's full review,
                  a bug scan, a correction review) -- lower concurrency,
                  these are genuinely slow (gemma4 alone: 2-4 min/call).
  - infra         system-level checks (Sentinel health, Security
                  posture) -- fast, deterministic, no model call.
"""
from . import bug_fixer, chrome_developer, correction_bot, finance, security, sentinel, website_audit

WORKER_TYPES = ("rapid", "engineering", "infra")


def _task_website_audit(payload: dict) -> dict:
    return website_audit.run_website_audit(payload["url"])


def _task_finance_report(payload: dict) -> dict:
    return finance.generate_report(payload.get("period", "monthly"), business_id=payload.get("business_id"))


def _task_website_review(payload: dict) -> dict:
    return chrome_developer.review_website(payload["url"], business_id=payload.get("business_id"))


def _task_bug_scan(payload: dict) -> dict:
    return {"candidates": bug_fixer.scan_for_bugs()}


def _task_correction_review(payload: dict) -> dict:
    return correction_bot.review_and_correct(payload["task_type"], payload.get("task_ref"), payload["content"],
                                              business_id=payload.get("business_id"))


def _task_security_posture_scan(payload: dict) -> dict:
    return security.security_posture_scan()


def _task_sentinel_health_check(payload: dict) -> dict:
    return sentinel.collect_health()


# kind -> (worker_type, callable(payload: dict) -> dict)
TASK_KINDS = {
    "website_audit": ("rapid", _task_website_audit),
    "finance_report": ("rapid", _task_finance_report),
    "website_review": ("engineering", _task_website_review),
    "bug_scan": ("engineering", _task_bug_scan),
    "correction_review": ("engineering", _task_correction_review),
    "security_posture_scan": ("infra", _task_security_posture_scan),
    "sentinel_health_check": ("infra", _task_sentinel_health_check),
}


def worker_type_for_kind(kind: str) -> str:
    if kind not in TASK_KINDS:
        raise ValueError(f"unknown task kind '{kind}' — expected one of {list(TASK_KINDS)}")
    return TASK_KINDS[kind][0]


def run_task(kind: str, payload: dict) -> dict:
    """The only place a task kind's payload dict meets its real callable
    -- no business decision made here, just dispatch + execute."""
    if kind not in TASK_KINDS:
        raise ValueError(f"unknown task kind '{kind}' — expected one of {list(TASK_KINDS)}")
    _, fn = TASK_KINDS[kind]
    return fn(payload)
