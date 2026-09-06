"""
Real tests for the Marketing agent -- content generation and the
marketing -> sales hand-off. Model calls mocked (no live Ollama
dependency), same pattern as test_sales.py.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import db, marketing, model_gateway, routing


class MarketingTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_marketing_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()
        from orchestrator import registry
        registry.sync_registry()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestGenerateContent(MarketingTestBase):
    def test_generates_requested_variant_count_with_distinct_angles(self):
        calls = []

        def fake_call_local(model, role_prompt, prompt):
            calls.append(prompt)
            return ("Some landing copy.\nICP_FIT: 0.75", 20, 15)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            results = marketing.generate_content(None, "landing_copy", "founders", "our offer", count=3)

        self.assertEqual(len(results), 3)
        self.assertEqual([r["variant"] for r in results], ["A", "B", "C"])
        # each call got a genuinely different angle instruction, not the same prompt 3x
        self.assertEqual(len(set(calls[:3])), 3)

    def test_icp_fit_parsed_and_stripped_from_content(self):
        def fake_call_local(model, role_prompt, prompt):
            return ("Great copy here.\nICP_FIT: 0.88", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            results = marketing.generate_content(None, "cold_email", "founders", "offer", count=1)

        self.assertEqual(results[0]["icp_fit"], 0.88)
        self.assertNotIn("ICP_FIT", results[0]["content"])

    def test_creates_real_marketing_task_rows(self):
        def fake_call_local(model, role_prompt, prompt):
            return ("Copy.\nICP_FIT: 0.5", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            marketing.generate_content(None, "ad_angle", "founders", "offer", count=2)

        with db.get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE agent_id = 'marketing'").fetchone()["c"]
        self.assertEqual(count, 2)


class TestSendToSales(MarketingTestBase):
    def test_marks_content_sent_and_creates_real_sales_task(self):
        def fake_call_local(model, role_prompt, prompt):
            return ("Content.\nICP_FIT: 0.6", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            [content] = marketing.generate_content(None, "landing_copy", "founders", "offer", count=1)
            result = marketing.send_to_sales(content["content_id"])

        self.assertEqual(result["status"], "done")
        with db.get_conn() as conn:
            row = db.get_content(conn, content["content_id"])
            sales_tasks = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE agent_id = 'sales'").fetchone()["c"]
        self.assertEqual(row["status"], "sent_to_sales")
        self.assertEqual(sales_tasks, 1)


if __name__ == "__main__":
    unittest.main()
