"""
ui_review_engine.py. Covers the deterministic scoring/findings logic
offline. run_browser_audit() itself (the real Playwright subprocess call)
is exercised live in this session against real URLs -- see chat history:
example.com (233ms, 0 errors) and dhansetuhub.in (9259ms, 0 errors, no
CTA) -- not re-mocked here since a fake subprocess result would just be
testing the mock, not the real integration.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import ui_review_engine as ui


GOOD_RESULT = {
    "ok": True, "load_time_ms": 500, "console_error_count": 0, "console_errors": [],
    "has_cta": True, "mobile_renders_without_overflow": True,
}

BAD_RESULT = {
    "ok": True, "load_time_ms": 9259, "console_error_count": 3,
    "console_errors": ["TypeError: x is not a function", "404 for /missing.js", "Uncaught ReferenceError"],
    "has_cta": False, "mobile_renders_without_overflow": False,
}


class TestConversionScore(unittest.TestCase):
    def test_fast_clean_page_scores_100(self):
        self.assertEqual(ui.conversion_score(GOOD_RESULT), 100)

    def test_slow_broken_page_scores_low(self):
        score = ui.conversion_score(BAD_RESULT)
        self.assertLess(score, 40)

    def test_score_never_negative(self):
        worst = {"load_time_ms": 60000, "console_error_count": 20, "has_cta": False, "mobile_renders_without_overflow": False}
        self.assertEqual(ui.conversion_score(worst), 0)

    def test_moderate_load_time_small_penalty(self):
        mid = {**GOOD_RESULT, "load_time_ms": 2500}
        self.assertLess(ui.conversion_score(mid), 100)
        self.assertGreaterEqual(ui.conversion_score(mid), 90)


class TestUiFindings(unittest.TestCase):
    def test_clean_result_has_no_findings(self):
        self.assertEqual(ui.ui_findings(GOOD_RESULT), [])

    def test_bad_result_flags_everything(self):
        findings = ui.ui_findings(BAD_RESULT)
        categories = [f[0] for f in findings]
        self.assertIn("performance", categories)
        self.assertIn("console_error", categories)
        self.assertIn("conversion", categories)
        self.assertIn("mobile", categories)

    def test_each_console_error_becomes_its_own_finding(self):
        findings = ui.ui_findings(BAD_RESULT)
        console_findings = [f for f in findings if f[0] == "console_error"]
        self.assertEqual(len(console_findings), 3)


class TestRunBrowserAuditErrorHandling(unittest.TestCase):
    def test_missing_script_raises(self):
        orig = ui.BROWSER_SCRIPT
        ui.BROWSER_SCRIPT = Path("/nonexistent/browser_audit.js")
        try:
            with self.assertRaises(ui.BrowserAuditError):
                ui.run_browser_audit("https://example.com")
        finally:
            ui.BROWSER_SCRIPT = orig


if __name__ == "__main__":
    unittest.main()
