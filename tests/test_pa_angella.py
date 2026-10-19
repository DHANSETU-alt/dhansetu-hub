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


class TestTeam2Reachable(PaAngellaTestBase):
    """Real regression test for the 5-Why fix, 2026-09-09: ceo_2 (Team 2's
    CEO) existed in the registry as data since the double-team was built,
    but ceo.decide() and refine_and_send_to_ceo() hardcoded 'ceo' as a
    literal -- Team 2 was completely unreachable through any real code
    path. Confirms the parameterized fix actually routes to Team 2, and
    that Team 1 behavior is unchanged (no regression from the default)."""

    def test_ceo_decide_can_route_to_team_2(self):
        def fake_call_local(model, role_prompt, prompt):
            return ('```json\n{"status": "approved", "priority_score": 5, "risk_score": 2, '
                    '"business_impact_score": 4, "reason": "fine"}\n```', 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            from orchestrator import ceo
            ceo.decide("test goal", agent_id="ceo_2")

        with db.get_conn() as conn:
            team1_count = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE agent_id = 'ceo'").fetchone()["c"]
            team2_count = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE agent_id = 'ceo_2'").fetchone()["c"]
        self.assertEqual(team1_count, 0)
        self.assertEqual(team2_count, 1)

    def test_default_still_routes_to_team_1_no_regression(self):
        def fake_call_local(model, role_prompt, prompt):
            return ('```json\n{"status": "approved", "priority_score": 5, "risk_score": 2, '
                    '"business_impact_score": 4, "reason": "fine"}\n```', 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            from orchestrator import ceo
            ceo.decide("test goal")

        with db.get_conn() as conn:
            team1_count = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE agent_id = 'ceo'").fetchone()["c"]
        self.assertEqual(team1_count, 1)

    def test_refine_and_send_to_ceo_can_route_to_team_2(self):
        def fake_call_local(model, role_prompt, prompt):
            if "PA Angella" in role_prompt or "prompt-master" in role_prompt:
                return ("Refined goal.", 10, 10)
            return ('```json\n{"status": "approved", "priority_score": 5, "risk_score": 2, '
                    '"business_impact_score": 4, "reason": "fine"}\n```', 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            pa_angella.refine_and_send_to_ceo("raw ask", ceo_agent_id="ceo_2")

        with db.get_conn() as conn:
            ceo_count = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE agent_id = 'ceo'").fetchone()["c"]
            ceo2_count = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE agent_id = 'ceo_2'").fetchone()["c"]
        self.assertEqual(ceo_count, 0)
        self.assertEqual(ceo2_count, 1)


if __name__ == "__main__":
    unittest.main()
