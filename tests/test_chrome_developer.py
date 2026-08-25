"""
chrome_developer.py. Mocks ceo.decide(), the browser audit, and Telegram
to exercise the real orchestration + DB write path without needing a live
Ollama call or a live `node` subprocess in every test run -- the browser
audit itself (ui_review_engine.run_browser_audit) was exercised live
against real URLs this session (example.com, dhansetuhub.in).
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import chrome_developer as cd
from orchestrator import db
from orchestrator import telegram as tg

GOOD_HTML = b"""<!DOCTYPE html>
<html lang="en">
<head><title>Dhansetu Hub Tools</title>
<meta name="description" content="A description that is definitely long enough to pass the fifty character minimum threshold.">
<link rel="canonical" href="https://example.com/">
<meta property="og:title" content="Dhansetu Hub"><meta property="og:description" content="desc"><meta property="og:image" content="https://example.com/o.png">
<script type="application/ld+json">{}</script>
</head>
<body><h1>Dhansetu Hub Tools</h1></body></html>"""


class TestScanExposedSecrets(unittest.TestCase):
    def test_detects_aws_key(self):
        findings = cd.scan_exposed_secrets("var key = 'AKIAABCDEFGHIJKLMNOP';")
        self.assertTrue(any(f[1] == "P0" for f in findings))

    def test_clean_html_has_no_findings(self):
        self.assertEqual(cd.scan_exposed_secrets(GOOD_HTML.decode()), [])


class TestUiScore(unittest.TestCase):
    def test_all_good_scores_100(self):
        https = {"uses_https": True, "cert_valid": True}
        headers = {"present_count": 5}
        links = {"checked": 0, "broken_count": 0}
        browser = {"console_error_count": 0, "mobile_renders_without_overflow": True}
        self.assertEqual(cd._ui_score(https, headers, links, browser), 100)

    def test_no_browser_result_still_scores_reasonably(self):
        https = {"uses_https": True, "cert_valid": True}
        headers = {"present_count": 5}
        links = {"checked": 0, "broken_count": 0}
        score = cd._ui_score(https, headers, links, None)
        self.assertEqual(score, 100)

    def test_bad_signals_lower_score(self):
        https = {"uses_https": False, "cert_valid": None}
        headers = {"present_count": 0}
        links = {"checked": 5, "broken_count": 5}
        browser = {"console_error_count": 5, "mobile_renders_without_overflow": False}
        score = cd._ui_score(https, headers, links, browser)
        self.assertEqual(score, 0)


class TestFormatReport(unittest.TestCase):
    def test_contains_required_fields(self):
        text = cd.format_report("https://example.com", 90, 80, 70, True, 3, "2026-01-01 00:00:00 UTC")
        self.assertIn("SHAKTHI CHROME DEVELOPER REPORT", text)
        self.assertIn("SEO Score: 90/100", text)
        self.assertIn("Conversion Score: 80/100", text)
        self.assertIn("UI Score: 70/100", text)
        self.assertIn("Deployment Ready:\nYes", text)

    def test_none_conversion_score_shown_as_unavailable(self):
        text = cd.format_report("https://example.com", 90, None, 70, False, 3, "2026-01-01 00:00:00 UTC")
        self.assertIn("N/A", text)
        self.assertIn("Deployment Ready:\nNo", text)


class TestReviewWebsiteFullPipeline(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_cd_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _fake_fetch(self, url, method="GET", timeout=None):
        return {"ok": True, "status": 200, "headers": {"Strict-Transport-Security": "max-age=1"},
                "body": GOOD_HTML, "elapsed_ms": 100, "final_url": url, "error": None}

    def test_full_pipeline_stores_and_approves(self):
        from orchestrator import website_audit as wa

        with patch.object(wa, "fetch", self._fake_fetch), \
             patch.object(wa, "check_broken_links", return_value={"checked": 0, "broken": [], "broken_count": 0, "skipped_beyond_cap": 0}), \
             patch.object(cd.ui_review_engine, "run_browser_audit", return_value={
                 "ok": True, "load_time_ms": 400, "console_error_count": 0, "console_errors": [],
                 "has_cta": True, "mobile_renders_without_overflow": True,
             }), \
             patch.object(cd.ceo, "decide", return_value={"status": "approved", "reason": "looks good"}), \
             patch("orchestrator.telegram_service.resolve_credentials", side_effect=tg.TelegramError("no creds")):

            result = cd.review_website("https://example.com")

        self.assertTrue(result["deployment_ready"])
        self.assertEqual(result["seo_score"], 100)
        with db.get_conn() as conn:
            row = db.get_website_review(conn, result["review_id"])
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["deployment_ready"], 1)

    def test_browser_audit_failure_does_not_crash_pipeline(self):
        from orchestrator import website_audit as wa

        with patch.object(wa, "fetch", self._fake_fetch), \
             patch.object(wa, "check_broken_links", return_value={"checked": 0, "broken": [], "broken_count": 0, "skipped_beyond_cap": 0}), \
             patch.object(cd.ui_review_engine, "run_browser_audit", side_effect=cd.ui_review_engine.BrowserAuditError("node not found")), \
             patch.object(cd.ceo, "decide", return_value={"status": "approved", "reason": "ok"}), \
             patch("orchestrator.telegram_service.resolve_credentials", side_effect=tg.TelegramError("no creds")):

            result = cd.review_website("https://example.com")

        self.assertIsNone(result["conversion_score"])
        self.assertFalse(result["browser_audit_available"])
        with db.get_conn() as conn:
            row = db.get_website_review(conn, result["review_id"])
        self.assertEqual(row["status"], "completed")


if __name__ == "__main__":
    unittest.main()
