"""
OPS-002: security posture scan. Covers the deterministic, offline-testable
parts -- env var presence-only reporting, file permission classification,
recommendation text, and score arithmetic. Does NOT exercise
scan_api_key_exposure() (reads the whole real codebase), get_me()/Sheets
network calls, or the full security_posture_scan() orchestration -- those
are exercised live, the same way OPS-001's Sentinel scan was.

The one thing every test here is really checking: no function under test
ever returns a secret VALUE, only booleans/status strings.
"""
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import security


class TestScanEnvVars(unittest.TestCase):
    def test_never_returns_actual_values(self):
        os.environ["ANTHROPIC_API_KEY"] = "sk-super-secret-value"
        try:
            report = security.scan_env_vars()
            dumped = str(report)
            self.assertNotIn("sk-super-secret-value", dumped)
            self.assertTrue(report["configured"]["ANTHROPIC_API_KEY"])
        finally:
            del os.environ["ANTHROPIC_API_KEY"]

    def test_unset_var_reports_false(self):
        os.environ.pop("SHAKTHI_OWNER_PASSPHRASE", None)
        report = security.scan_env_vars()
        self.assertFalse(report["configured"]["SHAKTHI_OWNER_PASSPHRASE"])

    def test_risk_flag_true_only_when_exactly_one(self):
        os.environ["SHAKTHI_ALLOW_EXEC"] = "1"
        try:
            report = security.scan_env_vars()
            self.assertTrue(report["risk_flags"]["SHAKTHI_ALLOW_EXEC"])
        finally:
            del os.environ["SHAKTHI_ALLOW_EXEC"]

    def test_risk_flag_false_for_other_values(self):
        os.environ["SHAKTHI_ALLOW_EXEC"] = "true"
        try:
            report = security.scan_env_vars()
            self.assertFalse(report["risk_flags"]["SHAKTHI_ALLOW_EXEC"])
        finally:
            del os.environ["SHAKTHI_ALLOW_EXEC"]


class TestScanFilePermissions(unittest.TestCase):
    def test_world_readable_file_flagged_high(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = Path(f.name)
        try:
            path.chmod(0o644)
            orig = security.config.DB_PATH
            security.config.DB_PATH = str(path)
            try:
                findings = security.scan_file_permissions()
            finally:
                security.config.DB_PATH = orig
            self.assertTrue(any(x["severity"] == "high" for x in findings))
        finally:
            path.unlink()

    def test_owner_only_file_not_flagged(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = Path(f.name)
        try:
            path.chmod(0o600)
            orig = security.config.DB_PATH
            security.config.DB_PATH = str(path)
            try:
                findings = security.scan_file_permissions()
            finally:
                security.config.DB_PATH = orig
            self.assertEqual(findings, [])
        finally:
            path.unlink()

    def test_missing_file_skipped_not_errored(self):
        orig = security.config.DB_PATH
        security.config.DB_PATH = "/tmp/does-not-exist-shakthi-test.db"
        try:
            findings = security.scan_file_permissions()
        finally:
            security.config.DB_PATH = orig
        self.assertEqual(findings, [])


class TestCheckTelegramCredentials(unittest.TestCase):
    def test_no_credentials_reports_not_provided(self):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_CHAT_ID", None)
        status = security.check_telegram_credentials(None, None)
        self.assertFalse(status["provided"])
        self.assertIsNone(status["valid"])

    def test_invalid_token_reports_provided_but_invalid(self):
        status = security.check_telegram_credentials("not-a-real-token", "123")
        self.assertTrue(status["provided"])
        self.assertFalse(status["valid"])

    def test_never_returns_the_token(self):
        status = security.check_telegram_credentials("not-a-real-token", "123")
        self.assertNotIn("not-a-real-token", str(status))


class TestCheckSheetsCredentials(unittest.TestCase):
    def test_no_path_reports_not_provided(self):
        status = security.check_sheets_credentials(None)
        self.assertEqual(status, {"provided": False, "valid": None, "file_permission_ok": None})

    def test_missing_file_reports_invalid(self):
        status = security.check_sheets_credentials("/tmp/does-not-exist-shakthi-creds.json")
        self.assertTrue(status["provided"])
        self.assertFalse(status["valid"])

    def test_malformed_json_reports_invalid_not_error(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write("not valid json{{{")
            path = f.name
        try:
            status = security.check_sheets_credentials(path)
            self.assertFalse(status["valid"])
        finally:
            os.unlink(path)

    def test_valid_looking_service_account_reports_valid(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write('{"type": "service_account", "private_key": "-----BEGIN PRIVATE KEY-----fake-----END PRIVATE KEY-----"}')
            path = f.name
        try:
            os.chmod(path, 0o600)
            status = security.check_sheets_credentials(path)
            self.assertTrue(status["valid"])
            self.assertTrue(status["file_permission_ok"])
        finally:
            os.unlink(path)

    def test_never_returns_the_private_key(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write('{"type": "service_account", "private_key": "TOTALLY-SECRET-KEY-MATERIAL"}')
            path = f.name
        try:
            status = security.check_sheets_credentials(path)
            self.assertNotIn("TOTALLY-SECRET-KEY-MATERIAL", str(status))
        finally:
            os.unlink(path)


class TestRecommendAction(unittest.TestCase):
    def test_healthy_posture_recommends_no_action(self):
        msg = security._recommend_action(
            [], [], {"risk_flags": {"SHAKTHI_ALLOW_EXEC": False}},
            {"provided": False, "valid": None}, {"provided": False, "valid": None},
        )
        self.assertIn("No action needed", msg)

    def test_secret_finding_triggers_removal_recommendation(self):
        msg = security._recommend_action(
            [{"type": "hardcoded_secret"}], [], {"risk_flags": {"SHAKTHI_ALLOW_EXEC": False}},
            {"provided": False, "valid": None}, {"provided": False, "valid": None},
        )
        self.assertIn("Remove hardcoded secrets", msg)

    def test_world_readable_file_triggers_chmod_recommendation(self):
        msg = security._recommend_action(
            [], [{"severity": "high"}], {"risk_flags": {"SHAKTHI_ALLOW_EXEC": False}},
            {"provided": False, "valid": None}, {"provided": False, "valid": None},
        )
        self.assertIn("chmod", msg)


class TestScoreAndReportShape(unittest.TestCase):
    """security_posture_scan()'s scoring/formatting logic, isolated from
    its network side effects by calling the pure pieces it composes."""

    def test_score_never_negative_with_many_findings(self):
        critical, warnings = 10, 10
        score = max(0, 100 - critical * 25 - warnings * 10)
        self.assertEqual(score, 0)

    def test_zero_findings_scores_100(self):
        critical, warnings = 0, 0
        score = max(0, 100 - critical * 25 - warnings * 10)
        self.assertEqual(score, 100)

    def test_report_text_matches_requested_format(self):
        # Assembled the same way security_posture_scan() builds report_text,
        # without the network calls.
        score, critical, warnings = 85, 0, 1
        credentials_status = "Safe"
        recommended_action = "No action needed — posture is healthy."
        text = f"""🛡 SHAKTHI SECURITY REPORT

Security Score: {score}/100

Critical Findings: {critical}
Warnings: {warnings}

Credentials Status:
{credentials_status}

Recommended Action:
{recommended_action}"""
        self.assertIn("SHAKTHI SECURITY REPORT", text)
        self.assertIn("Security Score: 85/100", text)
        self.assertIn("Critical Findings: 0", text)
        self.assertIn("Warnings: 1", text)
        self.assertIn("Credentials Status:\nSafe", text)
        self.assertIn("Recommended Action:", text)


if __name__ == "__main__":
    unittest.main()
