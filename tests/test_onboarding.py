"""
Real tests for blackboxOps_OS AI Employee Onboarding, Stage 1 (Business
Discovery) only. Model calls mocked (no live Ollama dependency), same
pattern as test_sales.py/test_dhansetu_ai.py.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import db, model_gateway, onboarding, routing


class OnboardingTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_onboarding_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()
        from orchestrator import registry
        registry.sync_registry()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestStartDiscovery(OnboardingTestBase):
    def test_creates_real_row(self):
        discovery_id = onboarding.start_discovery({"business_name": "Sunrise Bakery", "industry": "Food & Beverage"})
        with db.get_conn() as conn:
            row = db.get_business_discovery(conn, discovery_id)
        self.assertEqual(row["business_name"], "Sunrise Bakery")
        self.assertEqual(row["status"], "intake")

    def test_requires_business_name(self):
        with self.assertRaises(ValueError):
            onboarding.start_discovery({"industry": "Food"})


class TestAnalyzeDiscovery(OnboardingTestBase):
    def test_parses_all_five_categories(self):
        discovery_id = onboarding.start_discovery({"business_name": "Sunrise Bakery", "main_challenges": "no online presence"})

        def fake_call_local(model, role_prompt, prompt):
            return (
                "REVENUE:\nSingle location caps revenue growth.\n"
                "OPERATIONAL:\nManual, paper-based order tracking.\n"
                "MARKETING:\nNo online presence at all.\n"
                "SALES:\nnot enough information given\n"
                "SUPPORT:\nnot enough information given", 20, 15,
            )

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            result = onboarding.analyze_discovery(discovery_id)

        self.assertIn("caps revenue growth", result["revenue_bottlenecks"])
        self.assertIn("paper-based", result["operational_bottlenecks"])
        self.assertIn("online presence", result["marketing_bottlenecks"])
        self.assertEqual(result["sales_bottlenecks"], "not enough information given")
        self.assertEqual(result["status"], "analyzed")

    def test_never_injects_memory_context(self):
        """The real bug found live twice (PA Angella, then this agent):
        unrelated prior-task context bleeding into the analysis. Assert
        the routing-level fix actually applies to this agent."""
        self.assertIn("business_analyst", routing.NO_MEMORY_CONTEXT)

    def test_creates_real_business_analyst_task(self):
        discovery_id = onboarding.start_discovery({"business_name": "Sunrise Bakery"})

        def fake_call_local(model, role_prompt, prompt):
            self.assertNotIn("Relevant memory", prompt)  # the actual regression check
            return ("REVENUE:\nA\nOPERATIONAL:\nB\nMARKETING:\nC\nSALES:\nD\nSUPPORT:\nE", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            onboarding.analyze_discovery(discovery_id)

        with db.get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE agent_id = 'business_analyst'").fetchone()["c"]
        self.assertEqual(count, 1)

    def test_raises_for_unknown_discovery(self):
        with self.assertRaises(ValueError):
            onboarding.analyze_discovery(9999)


if __name__ == "__main__":
    unittest.main()
