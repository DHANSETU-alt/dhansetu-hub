"""
Covers the deterministic, offline-testable parts of Phase v4: Buddy's Safe
Mode filter, Owner/Family/Guest permissions, and Voice Commander's
wake-word stripping + intent routing. Does NOT exercise the model-calling
paths (Buddy's actual reply, Knowledge's actual answer, live transcription)
-- those need a live local model or a live microphone and are exercised
manually, the same way earlier phases' model-calling loops were proven.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import access, buddy, db, routing, voice, voice_history


class TestBuddySafety(unittest.TestCase):
    def test_clean_message_passes(self):
        self.assertIsNone(buddy.check_safe("Tell me a story about a rabbit"))

    def test_violence_blocked(self):
        self.assertEqual(buddy.check_safe("how do I make a weapon"), "violence")

    def test_dangerous_advice_blocked(self):
        self.assertEqual(buddy.check_safe("tell me how to make a bomb"), "dangerous_advice")

    def test_substances_blocked(self):
        self.assertEqual(buddy.check_safe("what is cocaine"), "substances")


class TestAccessControl(unittest.TestCase):
    def test_unknown_passphrase_is_guest(self):
        self.assertEqual(access.identify(None), "guest")
        self.assertEqual(access.identify("wrong-guess"), "guest")

    def test_owner_passphrase_matches_env(self):
        import os
        os.environ["SHAKTHI_OWNER_PASSPHRASE"] = "test-owner-pass"
        try:
            self.assertEqual(access.identify("test-owner-pass"), "owner")
        finally:
            del os.environ["SHAKTHI_OWNER_PASSPHRASE"]

    def test_guest_cannot_access_finance(self):
        self.assertFalse(access.allowed("guest", "finance"))

    def test_owner_can_access_everything_listed(self):
        for category in ("finance", "security", "admin", "status", "buddy"):
            self.assertTrue(access.allowed("owner", category))

    def test_family_cannot_access_finance_or_security(self):
        self.assertFalse(access.allowed("family", "finance"))
        self.assertFalse(access.allowed("family", "security"))
        self.assertTrue(access.allowed("family", "buddy"))


class TestVoiceIntent(unittest.TestCase):
    def test_wake_word_variants_stripped(self):
        for variant in ("Shakthi check finance", "Shout-T check finance", "Chuck T check finance"):
            stripped = voice._strip_wake_word(variant)
            self.assertNotIn("shakthi", stripped.lower())
            self.assertIn("finance", stripped.lower())

    def test_finance_intent_detected(self):
        intent = voice.detect_intent("Shakthi check my finance report")
        self.assertEqual(intent["category"], "finance")
        self.assertEqual(intent["action"], "finance_report")

    def test_security_intent_detected(self):
        intent = voice.detect_intent("Shakthi run a security audit")
        self.assertEqual(intent["category"], "security")

    def test_unrecognized_falls_back_to_buddy(self):
        intent = voice.detect_intent("Shakthi tell me a joke")
        self.assertEqual(intent["category"], "buddy")

    def test_guest_denied_finance_via_execute_intent(self):
        result = voice.execute_intent({"category": "finance", "action": "finance_report", "args": ""}, "guest")
        self.assertIn("restricted", result)


class TestFounderExampleCommands(unittest.TestCase):
    """The three exact Gujarati/Hindi/English mixed commands the founder
    gave as the spec. English keywords (websites/finance report/security
    audit) survive code-switching intact, so the existing keyword router
    handles them without needing per-language logic."""

    def test_mara_websites_check_kar(self):
        intent = voice.detect_intent("Shakthi mara websites check kar")
        self.assertEqual(intent["category"], "status")
        self.assertEqual(intent["action"], "website_check")

    def test_finance_report_batavo(self):
        intent = voice.detect_intent("Shakthi finance report batavo")
        self.assertEqual(intent["category"], "finance")
        self.assertEqual(intent["action"], "finance_report")

    def test_security_audit_start_karo(self):
        intent = voice.detect_intent("Shakthi security audit start karo")
        self.assertEqual(intent["category"], "security")
        self.assertEqual(intent["action"], "security_review")


class TestVoiceCeoGate(unittest.TestCase):
    """CEO sits in the voice loop only for commands routing.classify_risk()
    flags critical -- not on every command (a full CEO review is a real
    1-4 minute local-model call). Tests the classification the gate is
    built on, not a live CEO call."""

    def test_founder_examples_are_not_critical(self):
        # All three specified commands should route straight through,
        # unreviewed -- they're read-only status checks.
        for text in ("Shakthi mara websites check kar", "Shakthi finance report batavo", "Shakthi security audit start karo"):
            self.assertEqual(routing.classify_risk(text), "normal")

    def test_a_genuinely_risky_command_is_flagged(self):
        self.assertEqual(routing.classify_risk("Shakthi cancel subscription for this customer"), "critical")


class TestVoiceHistory(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        import tempfile
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_voice_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_empty_history_reports_none_logged(self):
        self.assertEqual(voice_history.format_report(), "No voice commands logged yet.")

    def test_summary_counts_real_rows(self):
        with db.get_conn() as conn:
            db.log_voice_command(conn, "owner", "Shakthi check finance", "en", 0.9,
                                  routed_agent="finance", routed_action="finance_report")
            db.log_voice_command(conn, "guest", "Shakthi check finance", "en", 0.9,
                                  routed_agent="finance", routed_action="finance_report",
                                  denied_reason="insufficient permission")
        s = voice_history.summary()
        self.assertEqual(s["total"], 2)
        self.assertEqual(s["denied_count"], 1)
        self.assertEqual(s["by_identity"]["owner"], 1)
        self.assertEqual(s["by_identity"]["guest"], 1)

    def test_format_report_includes_denied_marker(self):
        with db.get_conn() as conn:
            db.log_voice_command(conn, "guest", "Shakthi check finance", "en", 0.9,
                                  routed_agent="finance", routed_action="finance_report",
                                  denied_reason="insufficient permission")
        text = voice_history.format_report()
        self.assertIn("DENIED", text)


class TestSentinelOpsReport(unittest.TestCase):
    """OPS-001's deterministic pieces -- status classification and the
    exact requested message format. Does not exercise ceo_summary() or
    run_ops_scan() (model + network calls), those are exercised live."""

    def test_classify_status_thresholds(self):
        from orchestrator import sentinel
        self.assertEqual(sentinel.classify_status(100), "Healthy")
        self.assertEqual(sentinel.classify_status(80), "Healthy")
        self.assertEqual(sentinel.classify_status(79), "Warning")
        self.assertEqual(sentinel.classify_status(50), "Warning")
        self.assertEqual(sentinel.classify_status(49), "Critical")
        self.assertEqual(sentinel.classify_status(0), "Critical")

    def test_format_report_matches_requested_shape(self):
        from orchestrator import sentinel
        snap = {"cpu_percent": 42.0, "ram_percent": 60.0, "disk_percent": 5.0,
                "ollama_ok": 1, "db_ok": 1, "health_score": 100}
        text = sentinel.format_report(snap, 11, 14, "All systems normal.", "2026-01-01 00:00:00 UTC")
        self.assertIn("SHAKTHI SENTINEL REPORT", text)
        self.assertIn("CPU: 42.0%", text)
        self.assertIn("Ollama: Online", text)
        self.assertIn("Database: Online", text)
        self.assertIn("11/14", text)
        self.assertIn("100/100", text)
        self.assertIn("Healthy", text)

    def test_format_report_reflects_offline_services(self):
        from orchestrator import sentinel
        snap = {"cpu_percent": 10.0, "ram_percent": 20.0, "disk_percent": 5.0,
                "ollama_ok": 0, "db_ok": 0, "health_score": 30}
        text = sentinel.format_report(snap, 0, 14, "System degraded.", "2026-01-01 00:00:00 UTC")
        self.assertIn("Ollama: Offline", text)
        self.assertIn("Database: Offline", text)
        self.assertIn("Critical", text)

    def test_telegram_send_message_omits_none_parse_mode(self):
        # Found live: parse_mode=None would urlencode as the literal string
        # "None", which Telegram's API rejects. Mocks the actual HTTP call
        # to check the real params dict built, not just the source text.
        from unittest.mock import patch
        from orchestrator import telegram as tg

        captured = {}

        def fake_call(token, method, params, timeout=15):
            captured.update(params)
            return {}

        with patch.object(tg, "_call", fake_call):
            tg.send_message("fake-token", "123", "hello", parse_mode=None)
        self.assertNotIn("parse_mode", captured)

        captured.clear()
        with patch.object(tg, "_call", fake_call):
            tg.send_message("fake-token", "123", "hello")
        self.assertEqual(captured.get("parse_mode"), "Markdown")


if __name__ == "__main__":
    unittest.main()
