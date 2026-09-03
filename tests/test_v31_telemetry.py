import unittest

from shakthi.release import release_identity
from shakthi.telemetry import TelemetryCollector


class TelemetryTests(unittest.TestCase):
    def test_release_identity_uses_central_version(self):
        release = release_identity()
        self.assertEqual(release["version"], "3.1.0")
        self.assertTrue(release["build"])

    def test_collector_has_explicit_sources_and_deterministic_score(self):
        data = TelemetryCollector().collect()
        self.assertEqual(data["source"], "LOCAL")
        self.assertIn(data["health"]["state"], {"HEALTHY", "ATTENTION", "CRITICAL"})
        self.assertGreaterEqual(data["health"]["score"], 0)
        self.assertLessEqual(data["health"]["score"], 100)
        self.assertIn("state", data["system"]["thermal"])


if __name__ == "__main__":
    unittest.main()
