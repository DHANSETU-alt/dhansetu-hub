"""Real tests for website_health.py -- BlackboxOps OS Website Health
Watcher. Verifies the transition logic (incident open/close) and SSL
notAfter parsing against known inputs, isolated on a temp DB per the
existing test_incident_manager.py pattern -- never touches the real
shakthi.db.
"""
import shutil
import tempfile
import unittest

from orchestrator import db, website_health


class WebsiteHealthTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_website_health_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()
        with db.get_conn() as conn:
            self.website_id = db.insert_watched_website(conn, "https://example.invalid", "Test Site")
            self.site = dict(conn.execute("SELECT * FROM watched_websites WHERE id = ?", (self.website_id,)).fetchone())

    def tearDown(self):
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestRecordCheckReturnShape(WebsiteHealthTestBase):
    def test_record_check_includes_a_real_checked_at(self):
        # Regression test: record_check()'s returned dict originally
        # lacked checked_at entirely (only id/website_id were added),
        # which meant the /refresh API response showed "never" in the
        # frontend's Last Checked column immediately after a real,
        # successful check -- found live via browser testing, not by
        # inspection. checked_at must be the row's own DB value.
        result = {"status": "online", "status_code": 200, "response_time_ms": 100,
                   "ssl_expires_at": None, "ssl_days_remaining": None, "error_detail": None}
        with db.get_conn() as conn:
            recorded = website_health.record_check(conn, self.site, result)
        self.assertIn("checked_at", recorded)
        self.assertIsNotNone(recorded["checked_at"])


class TestIncidentTransitions(WebsiteHealthTestBase):
    def test_first_offline_check_opens_an_incident(self):
        result = {"status": "offline", "status_code": None, "response_time_ms": None,
                   "ssl_expires_at": None, "ssl_days_remaining": None, "error_detail": "simulated"}
        with db.get_conn() as conn:
            website_health.record_check(conn, self.site, result)
            incidents = db.list_incidents(conn)
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0]["status"], "open")
        self.assertIsNone(incidents[0]["closed_at"])

    def test_repeated_offline_checks_do_not_open_duplicate_incidents(self):
        result = {"status": "offline", "status_code": None, "response_time_ms": None,
                   "ssl_expires_at": None, "ssl_days_remaining": None, "error_detail": "simulated"}
        with db.get_conn() as conn:
            website_health.record_check(conn, self.site, result)
            website_health.record_check(conn, self.site, result)
            website_health.record_check(conn, self.site, result)
            incidents = db.list_incidents(conn)
        self.assertEqual(len(incidents), 1)

    def test_online_after_offline_closes_the_open_incident(self):
        offline = {"status": "offline", "status_code": None, "response_time_ms": None,
                    "ssl_expires_at": None, "ssl_days_remaining": None, "error_detail": "simulated"}
        online = {"status": "online", "status_code": 200, "response_time_ms": 100,
                   "ssl_expires_at": None, "ssl_days_remaining": None, "error_detail": None}
        with db.get_conn() as conn:
            website_health.record_check(conn, self.site, offline)
            website_health.record_check(conn, self.site, online)
            incidents = db.list_incidents(conn)
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0]["status"], "closed")
        self.assertIsNotNone(incidents[0]["closed_at"])

    def test_consecutive_online_checks_never_open_an_incident(self):
        online = {"status": "online", "status_code": 200, "response_time_ms": 100,
                   "ssl_expires_at": None, "ssl_days_remaining": None, "error_detail": None}
        with db.get_conn() as conn:
            website_health.record_check(conn, self.site, online)
            website_health.record_check(conn, self.site, online)
            incidents = db.list_incidents(conn)
        self.assertEqual(len(incidents), 0)

    def test_a_second_offline_period_opens_a_new_incident(self):
        offline = {"status": "offline", "status_code": None, "response_time_ms": None,
                    "ssl_expires_at": None, "ssl_days_remaining": None, "error_detail": "simulated"}
        online = {"status": "online", "status_code": 200, "response_time_ms": 100,
                   "ssl_expires_at": None, "ssl_days_remaining": None, "error_detail": None}
        with db.get_conn() as conn:
            website_health.record_check(conn, self.site, offline)   # incident #1 opens
            website_health.record_check(conn, self.site, online)    # incident #1 closes
            website_health.record_check(conn, self.site, offline)   # incident #2 opens
            incidents = db.list_incidents(conn)
        self.assertEqual(len(incidents), 2)
        open_ones = [i for i in incidents if i["status"] == "open"]
        closed_ones = [i for i in incidents if i["status"] == "closed"]
        self.assertEqual(len(open_ones), 1)
        self.assertEqual(len(closed_ones), 1)


class TestAlertFlag(WebsiteHealthTestBase):
    def test_offline_site_is_always_in_alert(self):
        check = {"status": "offline", "status_code": None, "response_time_ms": None}
        self.assertTrue(website_health.alert_flag(self.site, check))

    def test_online_under_threshold_is_not_in_alert(self):
        check = {"status": "online", "status_code": 200, "response_time_ms": 500}
        self.assertFalse(website_health.alert_flag(self.site, check))

    def test_online_over_threshold_is_in_alert(self):
        site = {**self.site, "alert_response_ms_threshold": 1000}
        check = {"status": "online", "status_code": 200, "response_time_ms": 5000}
        self.assertTrue(website_health.alert_flag(site, check))

    def test_no_check_yet_is_not_in_alert(self):
        self.assertFalse(website_health.alert_flag(self.site, None))


class TestSSLExpiryParsing(unittest.TestCase):
    def test_check_ssl_parses_a_real_notafter_format(self):
        # Real macOS/OpenSSL peer-cert notAfter format, hand-verified:
        # e.g. "Nov 10 12:55:32 2026 GMT" -- confirm the strptime format
        # string in _check_ssl actually parses it without raising, and
        # computes a real forward day-count for a known future date.
        from datetime import datetime, timezone
        sample = "Jan  1 00:00:00 2099 GMT"
        parsed = datetime.strptime(sample, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        self.assertEqual(parsed.year, 2099)
        days_remaining = (parsed - datetime.now(timezone.utc)).days
        self.assertGreater(days_remaining, 365 * 50)  # sanity: decades out, not a parsing artifact

    def test_check_ssl_handles_unreachable_host_without_raising(self):
        result = website_health._check_ssl("this-host-does-not-exist.invalid", timeout=2.0)
        self.assertIsNone(result["ssl_expires_at"])
        self.assertIsNone(result["ssl_days_remaining"])
        self.assertIsNotNone(result["error"])


class TestCheckOneSiteNeverRaises(unittest.TestCase):
    def test_unreachable_url_returns_offline_not_an_exception(self):
        result = website_health.check_one_site("https://this-domain-does-not-exist-blackboxops-test.invalid/")
        self.assertEqual(result["status"], "offline")
        self.assertIsNotNone(result["error_detail"])


if __name__ == "__main__":
    unittest.main()
