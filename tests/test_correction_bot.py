"""
SHAKTHI Correction Bot. Covers the deterministic detection/scoring logic
offline, plus one full review_and_correct() run with the model-calling and
Telegram/Sheets edges mocked -- exercising the real DB write path and the
Task Complete -> Correction Review -> QA Review -> Security Review -> Final
Approval wiring without needing a live local model. The live model call
itself (model_review -> Ollama) is exercised manually, same as every other
model-calling path in this codebase.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import correction_bot as cb
from orchestrator import db
from orchestrator import telegram as tg


class TestScanPlaceholders(unittest.TestCase):
    def test_detects_todo(self):
        findings = cb.scan_placeholders("def f():\n    # TODO fix this\n    pass")
        self.assertTrue(any(f["category"] == "placeholder_text" for f in findings))

    def test_detects_lorem_ipsum(self):
        findings = cb.scan_placeholders("Lorem ipsum dolor sit amet")
        self.assertTrue(findings)

    def test_clean_content_no_findings(self):
        findings = cb.scan_placeholders("Revenue grew 12% this quarter across all three businesses.")
        self.assertEqual(findings, [])


class TestScanCodeQuality(unittest.TestCase):
    def test_detects_eval(self):
        findings = cb.scan_code_quality("result = eval(user_input)")
        self.assertTrue(any(f["category"] == "code_quality" for f in findings))

    def test_detects_hardcoded_secret(self):
        findings = cb.scan_code_quality('api_key = "sk-abcdef1234567890abcdef"')
        self.assertTrue(any(f["category"] == "secret" for f in findings))

    def test_clean_code_no_findings(self):
        findings = cb.scan_code_quality("def add(a, b):\n    return a + b\n")
        self.assertEqual(findings, [])


class TestScanWebsiteContent(unittest.TestCase):
    def test_flags_missing_title_and_description(self):
        findings = cb.scan_website_content("<html><body><h1>Hi</h1></body></html>")
        categories = [f["category"] for f in findings]
        self.assertIn("seo", categories)

    def test_non_html_content_returns_no_findings(self):
        findings = cb.scan_website_content("Just plain text, not a webpage.")
        self.assertEqual(findings, [])

    def test_clean_page_has_no_seo_findings(self):
        html = ('<html lang="en"><head><title>Good Title Here</title>'
                '<meta name="description" content="A description that is long enough to pass the fifty character minimum threshold easily."></head>'
                '<body><h1>One heading</h1><img src="a.png" alt="desc"></body></html>')
        findings = cb.scan_website_content(html)
        self.assertEqual([f for f in findings if f["category"] == "seo"], [])


class TestDeterministicReview(unittest.TestCase):
    def test_code_type_includes_code_quality_checks(self):
        findings = cb.deterministic_review("code", "eval(x)")
        self.assertTrue(any(f["category"] == "code_quality" for f in findings))

    def test_writing_type_skips_code_checks(self):
        findings = cb.deterministic_review("writing", "eval(x) mentioned in an article about security")
        self.assertEqual([f for f in findings if f["category"] == "code_quality"], [])


class TestSecurityReviewCorrection(unittest.TestCase):
    def test_passes_clean_content(self):
        result = cb.security_review_correction("def add(a, b):\n    return a + b\n")
        self.assertTrue(result["passed"])

    def test_fails_on_dangerous_pattern(self):
        result = cb.security_review_correction("subprocess.run(cmd, shell=True)")
        self.assertFalse(result["passed"])

    def test_fails_on_secret(self):
        result = cb.security_review_correction('token = "abcdef1234567890abcdefghijklmno"')
        self.assertFalse(result["passed"])


class TestScore(unittest.TestCase):
    def test_zero_issues_scores_100(self):
        self.assertEqual(cb._score(0), 100)

    def test_score_never_negative(self):
        self.assertEqual(cb._score(50), 0)

    def test_score_bounded_at_100(self):
        self.assertEqual(cb._score(-5), 100)


class TestFormatReport(unittest.TestCase):
    def test_contains_all_required_fields(self):
        text = cb.format_report("code", "bug_fixer:patch:12", 80, 90, 3, 3, "approved", "2026-01-01 00:00:00 UTC")
        self.assertIn("SHAKTHI CORRECTION REPORT", text)
        self.assertIn("Correction Score: 80/100", text)
        self.assertIn("Quality Score: 90/100", text)
        self.assertIn("Issues Found: 3", text)
        self.assertIn("Issues Fixed: 3", text)
        self.assertIn("approved", text)


class TestParseJsonBlock(unittest.TestCase):
    def test_parses_valid_block(self):
        text = 'Here you go:\n```json\n{"issues": [], "corrected_content": "hi", "quality_score": 95}\n```'
        parsed = cb._parse_json_block(text)
        self.assertEqual(parsed["quality_score"], 95)

    def test_returns_none_on_malformed(self):
        self.assertIsNone(cb._parse_json_block("not json at all"))


class TestReviewAndCorrectFullPipeline(unittest.TestCase):
    """Mocks the model-calling and network edges to exercise the real
    orchestration + DB write path without needing a live Ollama call."""

    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_correction_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()
        from orchestrator import registry
        registry.sync_registry()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_full_pipeline_approves_clean_content(self):
        with patch.object(cb.bug_fixer, "call_agent") as mock_call_agent, \
             patch.object(cb.ceo, "decide") as mock_decide, \
             patch("orchestrator.telegram_service.resolve_credentials", side_effect=tg.TelegramError("no creds")):

            def fake_call_agent(conn, task_id, agent_id, prompt):
                if agent_id == "correction_bot":
                    return '```json\n{"issues": [], "corrected_content": "Clean report text.", "quality_score": 95}\n```'
                if agent_id == "qa":
                    return "PASS looks fine"
                raise AssertionError(f"unexpected agent {agent_id}")

            mock_call_agent.side_effect = fake_call_agent
            mock_decide.return_value = {"status": "approved", "reason": "looks good"}

            result = cb.review_and_correct("writing", "test:ref:1", "Clean report text.")

        self.assertEqual(result["final_status"], "approved")
        self.assertEqual(result["quality_score"], 95)
        with db.get_conn() as conn:
            row = db.get_correction(conn, result["correction_id"])
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["final_status"], "approved")

    def test_security_failure_forces_revise_without_calling_ceo(self):
        with patch.object(cb.bug_fixer, "call_agent") as mock_call_agent, \
             patch.object(cb.ceo, "decide") as mock_decide, \
             patch("orchestrator.telegram_service.resolve_credentials", side_effect=tg.TelegramError("no creds")):

            def fake_call_agent(conn, task_id, agent_id, prompt):
                if agent_id == "correction_bot":
                    return '```json\n{"issues": [], "corrected_content": "subprocess.run(cmd, shell=True)", "quality_score": 80}\n```'
                if agent_id == "qa":
                    return "PASS"
                raise AssertionError(f"unexpected agent {agent_id}")

            mock_call_agent.side_effect = fake_call_agent

            result = cb.review_and_correct("code", "test:ref:2", "subprocess.run(cmd, shell=True)")

        self.assertEqual(result["final_status"], "revise")
        mock_decide.assert_not_called()


if __name__ == "__main__":
    unittest.main()
