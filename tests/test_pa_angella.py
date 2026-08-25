"""
Real tests for PA Angella -- the founder's prompt-master PA, sitting
between Founder and CEO. Model calls mocked (no live Ollama dependency),
same pattern as test_sales.py.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import db, model_gateway, pa_angella, routing


class PaAngellaTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_pa_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()
        from orchestrator import registry
        registry.sync_registry()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestRefinePrompt(PaAngellaTestBase):
    def test_returns_refined_prompt_and_creates_real_task(self):
        def fake_call_local(model, role_prompt, prompt):
            return ("Please review the Q3 marketing budget and approve or flag concerns.", 15, 20)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            result = pa_angella.refine_prompt("hey check q3 marketing budget pls approve or w/e")

        self.assertIn("Q3 marketing budget", result["refined_prompt"])
        with db.get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE agent_id = 'pa_angella'").fetchone()["c"]
        self.assertEqual(count, 1)


class TestRefineAndSendToCeo(PaAngellaTestBase):
    def test_chains_pa_then_ceo_two_real_tasks(self):
        calls = []

        def fake_call_local(model, role_prompt, prompt):
            calls.append(model)
            if "PA Angella" in role_prompt or "prompt-master" in role_prompt:
                return ("Refined: approve the marketing budget increase.", 10, 10)
            return ('```json\n{"status": "approved", "priority_score": 6, "risk_score": 3, '
                    '"business_impact_score": 5, "reason": "reasonable ask"}\n```', 20, 15)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            result = pa_angella.refine_and_send_to_ceo("pls approve budget increase for marketing")

        self.assertIn("refined_prompt", result)
        self.assertEqual(result["ceo_decision"]["status"], "approved")

        with db.get_conn() as conn:
            pa_count = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE agent_id = 'pa_angella'").fetchone()["c"]
            ceo_count = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE agent_id = 'ceo'").fetchone()["c"]
        self.assertEqual(pa_count, 1)
        self.assertEqual(ceo_count, 1)


if __name__ == "__main__":
    unittest.main()
