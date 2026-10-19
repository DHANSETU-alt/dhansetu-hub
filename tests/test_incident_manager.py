"""
ERT: incident_registry, ownership_engine, incident_manager, incident_scheduler.
Mocks the model call for postmortem narrative (tested separately/manually,
same as every other model-calling path in this codebase) and Telegram --
everything else runs against a real temp DB with real state transitions.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import db, incident_manager, incident_registry, incident_scheduler, ownership_engine
from orchestrator import telegram as tg


class IncidentTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_incident_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()
        from orchestrator import registry
        registry.sync_registry()
        self._tg_patch = patch("orchestrator.telegram_service.resolve_credentials", side_effect=tg.TelegramError("no creds"))
        self._tg_patch.start()

    def tearDown(self):
        import shutil
        self._tg_patch.stop()
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestIncidentRegistry(unittest.TestCase):
    def test_lookup_known_type(self):
        entry = incident_registry.lookup("website_down")
        self.assertEqual(entry["owner"], "chrome_developer")
        self.assertEqual(entry["severity"], "P1")

    def test_lookup_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            incident_registry.lookup("not_a_real_type")

    def test_lookup_by_category(self):
        entry = incident_registry.lookup_by_category("payment")
        self.assertEqual(entry["owner"], "finance_lead")

    def test_every_matrix_entry_has_required_fields(self):
        for incident_type, entry in incident_registry.OWNERSHIP_MATRIX.items():
            self.assertIn("owner", entry)
            self.assertIn("backup", entry)
            self.assertIn("support", entry)
            self.assertIn(entry["severity"], incident_registry.SEVERITY_LEVELS)


class TestOwnershipEngine(IncidentTestBase):
    def test_assigns_primary_owner_when_available(self):
        with db.get_conn() as conn:
            result = ownership_engine.assign_owner(conn, "customer_complaint")
        self.assertEqual(result["owner"], "customer_success_lead")
        self.assertFalse(result["escalated"])

    def test_human_role_owner_always_available(self):
        self.assertTrue(ownership_engine.is_owner_available("finance_lead"))

    def test_system_owner_health_check_failure_falls_back_to_backup(self):
        with patch("orchestrator.sentinel.collect_health", side_effect=RuntimeError("down")):
            with db.get_conn() as conn:
                result = ownership_engine.assign_owner(conn, "performance_degradation")
        self.assertEqual(result["owner"], "worker_pool")  # backup for sentinel
        self.assertFalse(result["escalated"])

    def test_both_primary_and_backup_down_escalates_to_governor(self):
        with patch.object(ownership_engine, "is_owner_available", return_value=False):
            with db.get_conn() as conn:
                result = ownership_engine.assign_owner(conn, "website_down")
        self.assertEqual(result["owner"], "governor")
        self.assertTrue(result["escalated"])

    def test_load_balancing_reassigns_when_owner_overloaded(self):
        with db.get_conn() as conn:
            for _ in range(ownership_engine.MAX_OPEN_INCIDENTS_PER_OWNER):
                incident_manager.create_incident("customer_complaint", "test load")
            result = ownership_engine.assign_owner(conn, "customer_complaint")
        self.assertEqual(result["owner"], "knowledge")  # backup for customer_success_lead
        self.assertIn("load-balanced", result["reason"])


class TestIncidentManagerStateMachine(IncidentTestBase):
    def test_create_incident_generates_real_number_and_assigns_owner(self):
        result = incident_manager.create_incident("website_down", "example.com is returning 500s")
        self.assertTrue(result["incident_number"].startswith("INC-"))
        self.assertEqual(result["owner"], "chrome_developer")

        with db.get_conn() as conn:
            row = db.get_incident(conn, incident_number=result["incident_number"])
        self.assertEqual(row["status"], "NEW")

    def test_incident_numbers_increment_per_year(self):
        r1 = incident_manager.create_incident("website_down", "first")
        r2 = incident_manager.create_incident("website_down", "second")
        n1 = int(r1["incident_number"].split("-")[-1])
        n2 = int(r2["incident_number"].split("-")[-1])
        self.assertEqual(n2, n1 + 1)

    def test_forward_transition_succeeds(self):
        r = incident_manager.create_incident("website_down", "test")
        updated = incident_manager.transition(r["incident_number"], "ACKNOWLEDGED")
        self.assertEqual(updated["status"], "ACKNOWLEDGED")
        self.assertIsNotNone(updated["acknowledged_at"])

    def test_backward_transition_rejected(self):
        r = incident_manager.create_incident("website_down", "test")
        incident_manager.transition(r["incident_number"], "INVESTIGATING")
        with self.assertRaises(incident_manager.IncidentError):
            incident_manager.transition(r["incident_number"], "NEW")

    def test_resolve_requires_root_cause_and_fix(self):
        r = incident_manager.create_incident("payment_failure", "razorpay timeout")
        resolved = incident_manager.resolve(r["incident_number"], root_cause="gateway timeout", fix_applied="retried successfully")
        self.assertEqual(resolved["status"], "RESOLVED")
        self.assertEqual(resolved["root_cause"], "gateway timeout")
        self.assertIsNotNone(resolved["resolved_at"])

    def test_close_requires_resolved_first(self):
        r = incident_manager.create_incident("payment_failure", "test")
        with self.assertRaises(incident_manager.IncidentError):
            incident_manager.close(r["incident_number"])

    def test_close_after_resolve_succeeds_and_skips_postmortem_when_asked(self):
        r = incident_manager.create_incident("payment_failure", "test")
        incident_manager.resolve(r["incident_number"], root_cause="x", fix_applied="y")
        closed = incident_manager.close(r["incident_number"], generate_postmortem=False)
        self.assertEqual(closed["status"], "CLOSED")
        self.assertIsNotNone(closed["closed_at"])

    def test_p0_severity_triggers_telegram_attempt(self):
        with patch("orchestrator.telegram_service.resolve_credentials", return_value=("tok", "chat")), \
             patch("orchestrator.telegram.send_message") as mock_send:
            incident_manager.create_incident("security_incident", "breach detected")
        mock_send.assert_called_once()
        self.assertIn("ERT", mock_send.call_args[0][2])

    def test_p3_severity_does_not_send_telegram(self):
        with patch("orchestrator.telegram_service.resolve_credentials", return_value=("tok", "chat")), \
             patch("orchestrator.telegram.send_message") as mock_send:
            incident_manager.create_incident("customer_complaint", "minor complaint")
        mock_send.assert_not_called()

    def test_mttr_computes_real_average(self):
        r1 = incident_manager.create_incident("payment_failure", "a")
        incident_manager.resolve(r1["incident_number"], "cause", "fix")
        with db.get_conn() as conn:
            conn.execute("UPDATE incidents SET created_at = datetime('now', '-10 minutes') WHERE incident_number = ?", (r1["incident_number"],))
        with db.get_conn() as conn:
            mttr = incident_manager.mttr_seconds(conn)
        self.assertIsNotNone(mttr)
        self.assertGreater(mttr, 0)


class TestIncidentScheduler(IncidentTestBase):
    def test_high_cpu_creates_incident(self):
        fake_health = {"cpu_percent": 95.0, "ram_percent": 10.0, "disk_percent": 10.0, "cpu_temp_c": None, "db_ok": 1, "ollama_ok": 1}
        with patch("orchestrator.sentinel.collect_health", return_value=fake_health), \
             patch("orchestrator.sentinel.service_status", return_value={"ollama": True, "database": True}):
            result = incident_scheduler.run_detection_sweep()
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["incidents_created"][0]["incident_type"], "resource_critical")

    def test_healthy_system_creates_no_incidents(self):
        fake_health = {"cpu_percent": 20.0, "ram_percent": 20.0, "disk_percent": 20.0, "cpu_temp_c": None, "db_ok": 1, "ollama_ok": 1}
        with patch("orchestrator.sentinel.collect_health", return_value=fake_health), \
             patch("orchestrator.sentinel.service_status", return_value={"ollama": True, "database": True}):
            result = incident_scheduler.run_detection_sweep()
        self.assertEqual(result["count"], 0)

    def test_sustained_condition_does_not_duplicate_incident(self):
        fake_health = {"cpu_percent": 95.0, "ram_percent": 10.0, "disk_percent": 10.0, "cpu_temp_c": None, "db_ok": 1, "ollama_ok": 1}
        with patch("orchestrator.sentinel.collect_health", return_value=fake_health), \
             patch("orchestrator.sentinel.service_status", return_value={"ollama": True, "database": True}):
            r1 = incident_scheduler.run_detection_sweep()
            r2 = incident_scheduler.run_detection_sweep()
        self.assertEqual(r1["count"], 1)
        self.assertEqual(r2["count"], 0)  # already an open incident of this type


if __name__ == "__main__":
    unittest.main()
