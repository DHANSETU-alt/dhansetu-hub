import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import config, load_manager


class TestShouldScale(unittest.TestCase):
    def test_under_threshold_does_not_scale(self):
        self.assertFalse(load_manager.should_scale(2, threshold=3))

    def test_over_threshold_scales(self):
        self.assertTrue(load_manager.should_scale(4, threshold=3))

    def test_at_threshold_does_not_scale(self):
        self.assertFalse(load_manager.should_scale(3, threshold=3))

    def test_uses_config_default_threshold(self):
        self.assertEqual(load_manager.should_scale(config.WORKER_QUEUE_SCALE_THRESHOLD + 1), True)


class TestQueueOverflow(unittest.TestCase):
    def test_under_max_not_overflowing(self):
        self.assertFalse(load_manager.is_queue_overflowing(config.WORKER_QUEUE_MAX_SIZE - 1))

    def test_over_max_is_overflowing(self):
        self.assertTrue(load_manager.is_queue_overflowing(config.WORKER_QUEUE_MAX_SIZE + 1))


class TestConcurrencyFor(unittest.TestCase):
    def test_low_queue_depth_uses_base_concurrency(self):
        c = load_manager.concurrency_for("rapid", queue_depth=1)
        self.assertEqual(c, config.WORKER_BASE_CONCURRENCY)

    def test_high_queue_depth_scales_to_ceiling(self):
        c = load_manager.concurrency_for("rapid", queue_depth=config.WORKER_QUEUE_SCALE_THRESHOLD + 5)
        self.assertEqual(c, config.WORKER_CONCURRENCY_LIMITS["rapid"])

    def test_unknown_worker_type_falls_back_to_base(self):
        c = load_manager.concurrency_for("nonexistent", queue_depth=1)
        self.assertEqual(c, config.WORKER_BASE_CONCURRENCY)


if __name__ == "__main__":
    unittest.main()
