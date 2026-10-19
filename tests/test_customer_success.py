"""
Real tests for the Client Success pipeline, same pattern as test_sales.py.
Model calls are mocked (no live Ollama dependency) -- what's under test is
the pipeline: does health scoring actually read product_usage/
product_subscriptions and write a real client_health_scores row, does an
at-risk flag produce a real customer_success task, does the alert-check's
dedup state work.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import alerts, customer_success, db, routing


class ClientSuccessTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._orig_state_path = alerts.STATE_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_cs_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        alerts.STATE_PATH = Path(self._tmp_dir) / ".alerts_sync_state.json"
        db.init_db()
        from orchestrator import registry
        registry.sync_registry()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        alerts.STATE_PATH = self._orig_state_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _make_won_lead(self, email="client@example.com", **overrides):
        with db.get_conn() as conn:
            lead_id = db.insert_lead(
                conn, overrides.get("business_id"), overrides.get("name", "Test Client"),
                email, overrides.get("contact"), overrides.get("source", "website_form"), overrides.get("notes"),
            )
            db.update_lead(conn, lead_id, status="won")
        return lead_id


class TestComputeHealthScore(ClientSuccessTestBase):
    def test_no_usage_no_subscription_scores_zero_not_skipped(self):
        lead_id = self._make_won_lead()
        result = customer_success.compute_health_score(lead_id)
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["signals"], {})

    def test_recent_usage_scores_high(self):
        lead_id = self._make_won_lead(email="active@example.com")
        with db.get_conn() as conn:
            db.increment_usage(conn, "active@example.com", "pdf_studio")
        result = customer_success.compute_health_score(lead_id)
        self.assertGreater(result["score"], 0)
        self.assertIn("days_since_last_use", result["signals"])

    def test_active_subscription_contributes_score(self):
        lead_id = self._make_won_lead(email="sub@example.com")
        with db.get_conn() as conn:
            sub_id = db.insert_subscription(conn, "sub@example.com", "pdf_studio", 499.0, "payu")
            db.activate_subscription(conn, sub_id, "2099-01-01 00:00:00")
        result = customer_success.compute_health_score(lead_id)
        self.assertEqual(result["signals"]["subscription_status"], "active")
        self.assertGreater(result["score"], 0)


class TestScoreClientHealth(ClientSuccessTestBase):
    def test_creates_a_real_client_health_score_row(self):
        lead_id = self._make_won_lead()
        customer_success.score_client_health(lead_id)
        with db.get_conn() as conn:
            row = db.latest_client_health_score(conn, lead_id)
        self.assertIsNotNone(row)
        self.assertEqual(row["lead_id"], lead_id)

    def test_logs_health_scored_event(self):
        lead_id = self._make_won_lead()
        customer_success.score_client_health(lead_id)
        with db.get_conn() as conn:
            events = db.list_client_health_events(conn, lead_id)
        self.assertTrue(any(e["event_type"] == "health_scored" for e in events))


class TestFlagAtRisk(ClientSuccessTestBase):
    def test_creates_a_real_customer_success_task_row(self):
        lead_id = self._make_won_lead()
        with patch.object(routing, "_try_cloud", return_value=("[unavailable]", "failed")):
            customer_success.flag_at_risk(lead_id, "no usage in 90 days")
        with db.get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE agent_id = 'customer_success'").fetchone()["c"]
        self.assertGreater(count, 0)


class TestScanAllClients(ClientSuccessTestBase):
    def test_scores_every_won_lead_only(self):
        won_id = self._make_won_lead(email="won@example.com")
        with db.get_conn() as conn:
            db.insert_lead(conn, None, "Not Won", "notwon@example.com", None, "website_form")  # status stays 'new'

        results = customer_success.scan_all_clients()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["lead_id"], won_id)


class TestCheckClientHealth(ClientSuccessTestBase):
    def test_alerts_only_on_new_at_risk_rows(self):
        lead_id = self._make_won_lead()
        customer_success.score_client_health(lead_id)  # no usage/subscription -> score 0, at risk

        state = {}
        with db.get_conn() as conn:
            messages = alerts.check_client_health(conn, state)
        self.assertEqual(len(messages), 1)
        self.assertIn("client_health_last_id", state)

    def test_second_check_does_not_resend_same_row(self):
        lead_id = self._make_won_lead()
        customer_success.score_client_health(lead_id)

        state = {}
        with db.get_conn() as conn:
            alerts.check_client_health(conn, state)
            second = alerts.check_client_health(conn, state)
        self.assertEqual(second, [])

    def test_healthy_client_does_not_alert(self):
        lead_id = self._make_won_lead(email="healthy@example.com")
        with db.get_conn() as conn:
            for _ in range(30):
                db.increment_usage(conn, "healthy@example.com", "pdf_studio")
        customer_success.score_client_health(lead_id)

        state = {}
        with db.get_conn() as conn:
            messages = alerts.check_client_health(conn, state)
        self.assertEqual(messages, [])


if __name__ == "__main__":
    unittest.main()
