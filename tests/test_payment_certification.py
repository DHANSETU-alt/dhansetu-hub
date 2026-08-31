"""Real tests for payment_certification.py -- SHAKTHI_OS 3.1 Phase 1."""
from orchestrator import payment_certification as cert


def test_fully_passing_integration_is_production_ready():
    signals = {k: True for k, _, _ in cert.CHECKLIST}
    result = cert.certify("Test Product", "PayU", "production", signals)
    assert result["result"] == "PRODUCTION READY"
    assert result["security_score"] == 100
    assert result["blocking_failures"] == []


def test_blackboxops_os_real_payu_state_is_not_production_ready():
    """Honest negative test using this session's real, verified findings:
    blackboxops-os's hash-signed PayU checkout API has never had real
    merchant secrets configured (confirmed via `wrangler secret list` ->
    [] on both the default env and env.production). The static PayU
    handle-link workaround the founder personally tested does NOT go
    through this code path at all -- no server-side verification, no
    signature check, no DB record, no reconciliation."""
    real_signals = {
        "server_side_amount_verification": False,  # no real secrets -> hash API never actually runs
        "gateway_signature_verified": False,        # same -- can't verify without the salt
        "https_enforced": True,                     # Cloudflare Workers are HTTPS-only by default
        "secrets_server_side_only": True,            # what secrets exist are server-side, just empty
        "webhook_idempotent": False,                 # no webhook handling built for this path
        "duplicate_payment_protected": False,
        "db_transaction_recorded": False,            # PayU handle-link payments never touch the payments table
        "reconciliation_exists": False,
        "refund_path_exists": False,                 # manual PayU dashboard only, not a real automated path
        "failure_flow_handled": False,
    }
    result = cert.certify("BlackboxOps_OS", "PayU", "production", real_signals)
    assert result["result"] == "NOT PRODUCTION READY"
    assert "Server computes the real charge amount -- never trusts a client-supplied price" in result["blocking_failures"]
    assert result["security_score"] < 100


def test_missing_signal_defaults_to_not_certified_not_silently_passed():
    result = cert.certify("Test", "PayU", "production", {})
    assert result["result"] == "NOT PRODUCTION READY"
    assert result["security_score"] == 0
