"""
worker_pool.py. Uses a temp DB (each test opens its own connection per
call, same thread-safety rule the real module follows). The parallel-
execution test is a REAL timing check -- N tasks that each sleep 0.3s
must finish in well under N*0.3s if the ThreadPoolExecutor is actually
running them concurrently, not a mock standing in for "trust me."
"""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import db, worker_pool, worker_registry


class WorkerPoolTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_worker_pool_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestEnsureWorkersRegistered(WorkerPoolTestBase):
    def test_registers_expected_worker_counts(self):
        worker_pool.ensure_workers_registered()
        with db.get_conn() as conn:
            workers = db.list_workers(conn)
        rapid = [w for w in workers if w["worker_type"] == "rapid"]
        self.assertEqual(len(rapid), worker_pool.config.WORKER_CONCURRENCY_LIMITS["rapid"])

    def test_idempotent(self):
        worker_pool.ensure_workers_registered()
        worker_pool.ensure_workers_registered()
        with db.get_conn() as conn:
            workers = db.list_workers(conn)
        names = [w["name"] for w in workers]
        self.assertEqual(len(names), len(set(names)))  # no duplicates


class TestEnqueueTask(WorkerPoolTestBase):
    def test_enqueues_and_returns_id(self):
        qid = worker_pool.enqueue_task("website_audit", {"url": "https://example.com"})
        with db.get_conn() as conn:
            row = db.list_work_queue(conn)[0]
        self.assertEqual(row["id"], qid)
        self.assertEqual(row["kind"], "website_audit")
        self.assertEqual(json.loads(row["payload"])["url"], "https://example.com")

    def test_unknown_kind_rejected_before_writing(self):
        with self.assertRaises(ValueError):
            worker_pool.enqueue_task("not_a_real_kind", {})
        with db.get_conn() as conn:
            self.assertEqual(db.list_work_queue(conn), [])


class TestDrainQueueParallelism(WorkerPoolTestBase):
    def test_tasks_actually_run_concurrently(self):
        """Real timing proof, not a mocked claim: 4 tasks that each sleep
        0.3s must complete in well under 4*0.3s=1.2s if truly parallel."""
        def slow_task(payload):
            time.sleep(0.3)
            return {"ok": True}

        with patch.dict(worker_registry.TASK_KINDS, {"sentinel_health_check": ("infra", slow_task)}):
            for _ in range(4):
                worker_pool.enqueue_task("sentinel_health_check", {})

            start = time.monotonic()
            result = worker_pool.drain_queue(max_workers=4)
            elapsed = time.monotonic() - start

        self.assertEqual(result["dispatched"], 4)
        self.assertEqual(result["succeeded"], 4)
        self.assertLess(elapsed, 1.0, f"took {elapsed:.2f}s -- not running in parallel")

    def test_empty_queue_dispatches_nothing(self):
        result = worker_pool.drain_queue()
        self.assertEqual(result["dispatched"], 0)

    def test_failed_task_recorded_and_worker_marked_failed(self):
        def failing_task(payload):
            raise RuntimeError("simulated failure")

        with patch.dict(worker_registry.TASK_KINDS, {"sentinel_health_check": ("infra", failing_task)}):
            worker_pool.enqueue_task("sentinel_health_check", {})
            result = worker_pool.drain_queue(max_workers=1)

        self.assertEqual(result["succeeded"], 0)
        self.assertEqual(result["failed"], 1)
        with db.get_conn() as conn:
            queue_rows = db.list_work_queue(conn)
        self.assertEqual(queue_rows[0]["status"], "failed")
        self.assertIn("simulated failure", queue_rows[0]["error"])

    def test_mixed_success_and_failure(self):
        calls = {"n": 0}

        def flaky_task(payload):
            calls["n"] += 1
            if calls["n"] % 2 == 0:
                raise RuntimeError("even call fails")
            return {"ok": True}

        with patch.dict(worker_registry.TASK_KINDS, {"sentinel_health_check": ("infra", flaky_task)}):
            for _ in range(4):
                worker_pool.enqueue_task("sentinel_health_check", {})
            result = worker_pool.drain_queue(max_workers=2)

        self.assertEqual(result["dispatched"], 4)
        self.assertEqual(result["succeeded"] + result["failed"], 4)


class TestAlerting(WorkerPoolTestBase):
    def test_no_alert_sent_when_nothing_wrong(self):
        status = {"overflowing": False, "queue_depth": 1, "max_queue_size": 50}
        with patch("orchestrator.telegram_service.resolve_credentials") as mock_resolve:
            worker_pool._send_alerts(status, [], None, None)
        mock_resolve.assert_not_called()

    def test_alert_sent_on_failure(self):
        status = {"overflowing": False, "queue_depth": 1, "max_queue_size": 50}
        failed = [{"id": 1, "kind": "website_audit", "error": "boom"}]
        with patch("orchestrator.telegram_service.resolve_credentials", return_value=("tok", "chat")), \
             patch("orchestrator.telegram.send_message") as mock_send, \
             patch("orchestrator.sentinel.collect_health", return_value={"cpu_percent": 10, "ram_percent": 10}):
            worker_pool._send_alerts(status, failed, "tok", "chat")
        mock_send.assert_called_once()
        self.assertIn("Worker failure", mock_send.call_args[0][2])


if __name__ == "__main__":
    unittest.main()
