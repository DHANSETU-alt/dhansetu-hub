"""
Real bug found live, tasks #19 and #20: QA was rejecting CEO's own valid
"revise" decisions as if declining to approve were itself a QA failure,
which forced an escalation attempt that then failed (no ANTHROPIC_API_KEY)
and discarded the real local decision entirely, replacing it with an
unparseable placeholder string. Two fixes, tested here:
  1. routing.run_task() no longer sends `ceo`'s output through QA at all
     (same exemption qa/memory already had) -- a decision task's job is
     to render a judgment, and "revise" is a legitimate judgment.
  2. _try_cloud() falls back to the local model's real output when cloud
     escalation is unavailable, instead of discarding it.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import db, model_gateway, routing


class TestCeoSkipsQa(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_routing_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()
        from orchestrator import registry
        registry.sync_registry()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_ceo_normal_risk_never_calls_qa_or_escalates(self):
        """A CEO decision that would previously fail QA should now go
        straight to 'done' -- no QA call, no escalation attempt."""
        def fake_call_local(model, role_prompt, prompt):
            return ('```json\n{"status": "revise", "priority_score": 5, "risk_score": 3, '
                    '"business_impact_score": 4, "reason": "needs more review"}\n```', 50, 30)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local) as mock_local, \
             patch.object(routing, "_validate") as mock_validate, \
             patch.object(routing, "_try_cloud") as mock_cloud:
            result = routing.run_task("ceo", "Approve this correction?")

        self.assertEqual(result["status"], "done")
        self.assertFalse(result["escalated"])
        mock_validate.assert_not_called()
        mock_cloud.assert_not_called()
        self.assertEqual(mock_local.call_count, 2)  # ceo call + memory-write call, no QA call

    def test_ceo_decision_is_parseable_end_to_end(self):
        """The actual regression: a real 'revise' decision must survive
        intact and be parseable by ceo._parse_decision(), not get
        replaced by an escalation-unavailable placeholder."""
        from orchestrator import ceo

        def fake_call_local(model, role_prompt, prompt):
            return ('```json\n{"status": "revise", "priority_score": 5, "risk_score": 3, '
                    '"business_impact_score": 4, "reason": "needs more review"}\n```', 50, 30)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local):
            result = ceo.decide("Approve this correction?")

        self.assertEqual(result["status"], "revise")
        self.assertEqual(result["reason"], "needs more review")
        self.assertNotIn("could not parse", result["reason"])


class TestTryCloudLocalFallback(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_routing_test2_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()
        from orchestrator import registry
        registry.sync_registry()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_falls_back_to_local_text_when_cloud_unavailable(self):
        with db.get_conn() as conn:
            task_id = db.insert_task(conn, "engineer", "test goal", None, "normal")
            with patch.object(model_gateway, "call_cloud", side_effect=model_gateway.ModelError("no key")):
                text, status = routing._try_cloud(conn, task_id, {"id": "engineer", "role_prompt": "x"},
                                                   "prompt", local_fallback_text="the real local answer")

        self.assertIn("the real local answer", text)
        self.assertEqual(status, "done_local_fallback")

    def test_no_fallback_available_keeps_old_behavior(self):
        with db.get_conn() as conn:
            task_id = db.insert_task(conn, "engineer", "test goal", None, "normal")
            with patch.object(model_gateway, "call_cloud", side_effect=model_gateway.ModelError("no key")):
                text, status = routing._try_cloud(conn, task_id, {"id": "engineer", "role_prompt": "x"}, "prompt")

        self.assertEqual(status, "failed")
        self.assertIn("escalation unavailable", text)


class TestCriticalRiskLocalFallback(unittest.TestCase):
    """Real bug found live: tasks #10, #11, #19, #20 -- every critical-risk
    CEO decision (cancel subscription, delete records, launch readiness)
    with no ANTHROPIC_API_KEY produced status='failed' and zero real
    judgment call, because run_task()'s critical branch called _try_cloud()
    with no fallback at all. Fixed by passing a lazy local_fallback_fn."""

    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_routing_test3_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()
        from orchestrator import registry
        registry.sync_registry()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_critical_ceo_decision_falls_back_to_local_instead_of_failing(self):
        from orchestrator import ceo

        def fake_call_local(model, role_prompt, prompt):
            return ('```json\n{"status": "revise", "priority_score": 9, "risk_score": 9, '
                    '"business_impact_score": 9, "reason": "needs human review before refund"}\n```', 50, 30)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(model_gateway, "call_cloud", side_effect=model_gateway.ModelError("no key")):
            result = ceo.decide("Approve a refund for this customer's disputed charge")

        # The old behavior: status='failed', reason='could not parse...'.
        # The fix: a real, parseable decision, explicitly marked as not
        # cloud-confirmed rather than silently discarded.
        self.assertEqual(result["status"], "revise")
        self.assertEqual(result["reason"], "needs human review before refund")

    def test_cloud_available_never_pays_local_model_cost(self):
        """Lazy fallback: when cloud succeeds, the local model must never
        be called at all -- no wasted Ollama call on the common path."""
        def fake_call_cloud(role_prompt, prompt):
            return '```json\n{"status": "approved", "priority_score": 5, "risk_score": 2, ' \
                   '"business_impact_score": 5, "reason": "fine"}\n```', 50, 30

        with patch.object(model_gateway, "call_cloud", side_effect=fake_call_cloud), \
             patch.object(model_gateway, "call_local", return_value=("memory summary", 10, 5)) as mock_local:
            result = routing.run_task("ceo", "Delete all customer records older than 2 years")

        self.assertEqual(result["status"], "done")
        # one call for _write_memory only -- none for a local CEO fallback
        self.assertEqual(mock_local.call_count, 1)


if __name__ == "__main__":
    unittest.main()
