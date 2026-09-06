"""
Real tests for the Sales agent activation. Model calls are mocked (no live
Ollama dependency, same pattern as test_routing_ceo_fix.py) -- what's under
test is the pipeline: does a lead ingestion actually produce a real `tasks`
row with agent_id='sales', does scoring parse correctly (or fail closed),
does the escalation threshold route to the right place.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import db, model_gateway, routing, sales


class SalesTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_sales_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()
        from orchestrator import registry
        registry.sync_registry()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _make_lead(self, **overrides):
        with db.get_conn() as conn:
            return db.insert_lead(
                conn, overrides.get("business_id"), overrides.get("name", "Test Lead"),
                overrides.get("email", "lead@example.com"), overrides.get("contact"),
                overrides.get("source", "website_form"), overrides.get("notes"),
            )


class TestScoreLead(SalesTestBase):
    def test_parses_score_and_intent(self):
        lead_id = self._make_lead()

        def fake_call_local(model, role_prompt, prompt):
            return ("SCORE: 0.65\nINTENT: 0.40\nREASON: Decent fit, no urgency signals.", 20, 15)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            result = sales.score_lead(lead_id)

        self.assertEqual(result["score"], 0.65)
        self.assertEqual(result["intent"], 0.40)
        self.assertIn("Decent fit", result["reason"])

        with db.get_conn() as conn:
            lead = db.get_lead(conn, lead_id)
        self.assertEqual(lead["status"], "scored")
        self.assertEqual(lead["score"], 0.65)

    def test_unparseable_output_returns_none_not_fabricated(self):
        lead_id = self._make_lead()

        def fake_call_local(model, role_prompt, prompt):
            return ("I'm not sure how to score this lead.", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            result = sales.score_lead(lead_id)

        self.assertIsNone(result["score"])
        self.assertIsNone(result["intent"])

    def test_creates_a_real_sales_task_row(self):
        lead_id = self._make_lead()

        def fake_call_local(model, role_prompt, prompt):
            return ("SCORE: 0.5\nINTENT: 0.2\nREASON: ok.", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            sales.score_lead(lead_id)

        with db.get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE agent_id = 'sales'").fetchone()["c"]
        self.assertGreater(count, 0)


class TestDraftOutreach(SalesTestBase):
    def test_updates_lead_status_and_logs_event(self):
        lead_id = self._make_lead()

        def fake_call_local(model, role_prompt, prompt):
            return ("Subject: Hello\n\nHi there.", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            result = sales.draft_outreach(lead_id)

        self.assertIn("Subject:", result["draft"])
        with db.get_conn() as conn:
            lead = db.get_lead(conn, lead_id)
            events = db.list_lead_events(conn, lead_id)
        self.assertEqual(lead["status"], "contacted")
        self.assertTrue(any(e["event_type"] == "outreach_drafted" for e in events))


class TestFlagForFounder(SalesTestBase):
    def test_sets_owner_founder_even_if_cloud_unavailable(self):
        """Critical-risk tasks have no local fallback by design (matches
        the rest of this project) -- the lead must still get flagged even
        when the underlying escalation task itself fails."""
        lead_id = self._make_lead()

        with patch.object(routing, "_try_cloud", return_value=("[unavailable]", "failed")):
            result = sales.flag_for_founder(lead_id, "high intent")

        with db.get_conn() as conn:
            lead = db.get_lead(conn, lead_id)
        self.assertEqual(lead["owner"], "founder")
        self.assertEqual(lead["status"], "negotiating")
        self.assertEqual(result["status"], "failed")


class TestIngestLead(SalesTestBase):
    def test_high_intent_escalates_instead_of_drafting_outreach(self):
        def fake_call_local(model, role_prompt, prompt):
            return ("SCORE: 0.6\nINTENT: 0.9\nREASON: asked about custom pricing.", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")), \
             patch.object(routing, "_try_cloud", return_value=("[unavailable]", "failed")):
            result = sales.ingest_lead(None, "Hot Lead", "hot@example.com", "website_form")

        self.assertEqual(result["action"], "escalated_to_founder")

    def test_low_intent_drafts_outreach(self):
        def fake_call_local(model, role_prompt, prompt):
            return ("SCORE: 0.3\nINTENT: 0.1\nREASON: early stage.", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            result = sales.ingest_lead(None, "Cold Lead", "cold@example.com", "cold_list")

        self.assertEqual(result["action"], "outreach_drafted")

    def test_creates_a_real_lead_row(self):
        def fake_call_local(model, role_prompt, prompt):
            return ("SCORE: 0.4\nINTENT: 0.1\nREASON: ok.", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            result = sales.ingest_lead(None, "Someone", "someone@example.com", "referral")

        with db.get_conn() as conn:
            lead = db.get_lead(conn, result["lead_id"])
        self.assertEqual(lead["email"], "someone@example.com")
        self.assertEqual(lead["source"], "referral")


if __name__ == "__main__":
    unittest.main()
