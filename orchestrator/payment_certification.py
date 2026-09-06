"""SHAKTHI_OS 3.1 Phase 1 -- Payment Certification checklist.

Founder's own real "later" idea (recorded 2026-08-31): a hard
PRODUCTION READY / NOT PRODUCTION READY verdict for any payment
integration, blocking release when real security/reliability
requirements are missing. Deterministic checklist logic, not an AI
agent -- no model call, no fabricated scoring. The caller is
responsible for answering each signal honestly (from real code
inspection or a real config check); this module never guesses.

See SHAKTHI_OS_3.1_ULTRA_OMNI_ROADMAP.md, section 5/6/9/10.
"""

# Each item: (key, human label, whether missing this is a hard blocker)
CHECKLIST = [
    ("server_side_amount_verification", "Server computes the real charge amount -- never trusts a client-supplied price", True),
    ("gateway_signature_verified", "Gateway's response signature/hash is verified server-side before treating a payment as real", True),
    ("https_enforced", "All payment endpoints are HTTPS-only", True),
    ("secrets_server_side_only", "Merchant key/salt/secret never appears in client-side code or a public repo", True),
    ("webhook_idempotent", "A webhook received twice does not record the payment twice", True),
    ("duplicate_payment_protected", "A user double-clicking pay cannot be charged twice for the same order", True),
    ("db_transaction_recorded", "Every real payment attempt (success or failure) is recorded in a real database, not just logged", False),
    ("reconciliation_exists", "A real process compares internal payment records against the gateway's own records", False),
    ("refund_path_exists", "There is a real, working way to issue a refund (manual or automated)", False),
    ("failure_flow_handled", "A failed/declined payment shows the user a real, honest error, not a silent hang", False),
]


def certify(product: str, provider: str, environment: str, signals: dict) -> dict:
    """signals: dict mapping each CHECKLIST key to True/False, based on a
    real inspection of the actual integration -- never assumed or guessed.
    Missing keys are treated as False (unverified = not certified)."""
    results = []
    blocking_failures = []
    for key, label, is_blocker in CHECKLIST:
        passed = bool(signals.get(key, False))
        results.append({"key": key, "label": label, "passed": passed, "blocking": is_blocker})
        if is_blocker and not passed:
            blocking_failures.append(label)

    blocker_total = sum(1 for _, _, b in CHECKLIST if b)
    blocker_passed = sum(1 for r in results if r["blocking"] and r["passed"])
    nonblocker_total = len(CHECKLIST) - blocker_total
    nonblocker_passed = sum(1 for r in results if not r["blocking"] and r["passed"])

    security_score = round(100 * blocker_passed / blocker_total) if blocker_total else 100
    reliability_score = round(100 * nonblocker_passed / nonblocker_total) if nonblocker_total else 100
    overall_score = round((security_score + reliability_score) / 2)

    result = "PRODUCTION READY" if not blocking_failures else "NOT PRODUCTION READY"

    return {
        "product": product,
        "provider": provider,
        "environment": environment,
        "security_score": security_score,
        "reliability_score": reliability_score,
        "overall_score": overall_score,
        "result": result,
        "blocking_failures": blocking_failures,
        "checklist": results,
    }
