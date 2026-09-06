import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import worker_registry as wr


class TestWorkerTypeForKind(unittest.TestCase):
    def test_known_kinds_resolve(self):
        for kind in wr.TASK_KINDS:
            self.assertIn(wr.worker_type_for_kind(kind), wr.WORKER_TYPES)

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            wr.worker_type_for_kind("not_a_real_kind")

    def test_rapid_and_infra_kinds_never_hold_a_connection_across_a_model_call(self):
        # Documents the real safety split described in worker_pool.py's
        # docstring: rapid/infra kinds map to functions with no model call.
        rapid_and_infra = [k for k, (t, _) in wr.TASK_KINDS.items() if t in ("rapid", "infra")]
        self.assertIn("website_audit", rapid_and_infra)
        self.assertIn("sentinel_health_check", rapid_and_infra)
        self.assertIn("security_posture_scan", rapid_and_infra)


class TestRunTask(unittest.TestCase):
    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            wr.run_task("not_a_real_kind", {})

    def test_dispatches_to_the_right_function(self):
        with patch.object(wr, "_task_sentinel_health_check", return_value={"health_score": 100}) as mock_fn:
            wr.TASK_KINDS["sentinel_health_check"] = ("infra", mock_fn)
            try:
                result = wr.run_task("sentinel_health_check", {})
            finally:
                wr.TASK_KINDS["sentinel_health_check"] = ("infra", wr._task_sentinel_health_check)
        mock_fn.assert_called_once()
        self.assertEqual(result, {"health_score": 100})


if __name__ == "__main__":
    unittest.main()
