import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import db, governor


class GovernorTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_governor_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()
        from orchestrator import registry
        registry.sync_registry()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestCheckSubsystems(GovernorTestBase):
    def test_all_subsystems_reachable_with_no_ceo_involved(self):
        checks = governor.check_subsystems()
        self.assertTrue(checks["sentinel"]["ok"])
        self.assertTrue(checks["worker_pool"]["ok"])
        self.assertTrue(checks["security"]["ok"])
        self.assertTrue(checks["finance"]["ok"])

    def test_a_broken_subsystem_is_reported_not_raised(self):
        with patch("orchestrator.sentinel.collect_health", side_effect=RuntimeError("boom")):
            checks = governor.check_subsystems()
        self.assertFalse(checks["sentinel"]["ok"])
        self.assertIn("boom", checks["sentinel"]["detail"])
        # other subsystems still checked despite sentinel failing
        self.assertTrue(checks["worker_pool"]["ok"])


class TestFailoverEvents(GovernorTestBase):
    def test_no_events_when_ceo_healthy(self):
        with db.get_conn() as conn:
            db.insert_task(conn, "ceo", "a healthy decision", None, "normal")
            db.update_task(conn, 1, "done", "ok")
        with db.get_conn() as conn:
            events = governor.failover_events(conn)
        self.assertEqual(events, [])

    def test_failed_and_local_fallback_tasks_counted(self):
        with db.get_conn() as conn:
            t1 = db.insert_task(conn, "ceo", "goal one", None, "normal")
            db.update_task(conn, t1, "failed", "escalation unavailable")
            t2 = db.insert_task(conn, "ceo", "goal two", None, "normal")
            db.update_task(conn, t2, "done_local_fallback", "local answer used")
        with db.get_conn() as conn:
            events = governor.failover_events(conn)
        self.assertEqual(len(events), 2)


class TestGovernorStatus(GovernorTestBase):
    def test_operational_when_everything_healthy(self):
        with db.get_conn() as conn:
            status = governor.governor_status(conn)
        self.assertEqual(status["status"], "operational")
        self.assertEqual(status["failover_event_count_24h"], 0)

    def test_degraded_when_a_subsystem_is_down(self):
        with patch("orchestrator.sentinel.collect_health", side_effect=RuntimeError("boom")):
            with db.get_conn() as conn:
                status = governor.governor_status(conn)
        self.assertEqual(status["status"], "degraded")


if __name__ == "__main__":
    unittest.main()
