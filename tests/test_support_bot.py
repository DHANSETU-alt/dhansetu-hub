"""Real tests for the customer-facing Support Bot. Model calls are mocked
(no live Ollama dependency, same pattern as test_sales.py) -- what's under
test is the real pipeline: does a knowledge-base match answer straight
without touching leads, does an unmatched question with an email actually
produce a real `leads` row, does an unmatched question with no email ask
for one instead of silently dropping the question.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import db, knowledge, model_gateway, routing, support_bot


class SupportBotTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_support_bot_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()
        from orchestrator import registry
        registry.sync_registry()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestHandleMessage(SupportBotTestBase):
    def test_knowledge_base_match_answers_directly_no_lead_captured(self):
        knowledge.add_document("pricing", "Starter plan pricing", "Starter is ₹6,999/month.", tags="pricing")

        def fake_call_local(model, role_prompt, prompt):
            return ("Starter plan is ₹6,999 per month.", 20, 15)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local):
            result = support_bot.handle_message("How much is the starter plan?")

        self.assertTrue(result["matched"])
        self.assertFalse(result["lead_captured"])
        self.assertIn("₹6,999", result["answer"])
        self.assertEqual(result["sources"], ["Starter plan pricing"])

        with db.get_conn() as conn:
            leads = db.list_leads(conn)
        self.assertEqual(len(leads), 0)

    def test_unmatched_question_with_email_captures_a_real_lead(self):
        def fake_call_local(model, role_prompt, prompt):
            # Sales scoring/outreach calls also route through call_local --
            # a generic parseable response so ingest_lead's pipeline
            # (score_lead -> draft_outreach) completes without erroring.
            return ("SCORE: 0.50\nINTENT: 0.30\nREASON: New visitor, no signal yet.", 15, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            result = support_bot.handle_message(
                "Do you integrate with Tally?", email="visitor@example.com", name="Visitor",
            )

        self.assertFalse(result["matched"])
        self.assertTrue(result["lead_captured"])
        self.assertIn("lead_id", result)

        with db.get_conn() as conn:
            lead = conn.execute("SELECT * FROM leads WHERE id = ?", (result["lead_id"],)).fetchone()
        self.assertIsNotNone(lead)
        self.assertEqual(lead["email"], "visitor@example.com")
        self.assertEqual(lead["source"], "support_bot_unanswered")
        self.assertIn("Tally", lead["notes"])

    def test_unmatched_question_without_email_asks_for_one_no_lead(self):
        result = support_bot.handle_message("Do you integrate with Tally?")

        self.assertFalse(result["matched"])
        self.assertFalse(result["lead_captured"])
        self.assertIn("email", result["answer"].lower())

        with db.get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) AS c FROM leads").fetchone()["c"]
        self.assertEqual(count, 0)

    def test_empty_message_gets_a_helpful_prompt_not_an_error(self):
        result = support_bot.handle_message("   ")
        self.assertFalse(result["matched"])
        self.assertFalse(result["lead_captured"])
        self.assertTrue(len(result["answer"]) > 0)

    def test_never_leaks_internal_dashboard_data(self):
        # Real security boundary: this bot must never see or return the
        # founder's internal task/initiative snapshot the internal chat
        # widget uses. Confirms the response shape has no such field.
        result = support_bot.handle_message("hello")
        self.assertNotIn("tasks", result)
        self.assertNotIn("initiatives", result)
        self.assertNotIn("snapshot", str(result).lower())


if __name__ == "__main__":
    unittest.main()
