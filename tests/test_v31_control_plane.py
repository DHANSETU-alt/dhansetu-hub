import tempfile
import unittest
from pathlib import Path

from shakthi.angela import draft_mission
from shakthi.audit import AuditLog
from shakthi.governance import GovernanceError, assert_execution_allowed, next_confidence_action
from shakthi.missions import MissionStore
from shakthi.world_model import WorldModel


class ControlPlaneTests(unittest.TestCase):
    def test_angela_creates_complete_payment_mission(self):
        mission = draft_mission("Integrate PayU into DhanSetuHub", project="DhanSetuHub")
        record = mission.to_record()
        self.assertEqual(record["department"], "PaymentOps")
        self.assertEqual(record["current_status"], "PLANNED")
        self.assertEqual(record["confidence"]["required_action"], "DO_NOT_AUTONOMOUSLY_EXECUTE")

    def test_mission_is_persisted_and_audited(self):
        with tempfile.TemporaryDirectory() as temp:
            audit = AuditLog(Path(temp) / "audit.jsonl")
            store = MissionStore(Path(temp) / "missions.db", audit)
            mission = draft_mission("Build a web application")
            store.create(mission)
            self.assertEqual(store.get(mission.mission_id)["mission_id"], mission.mission_id)
            self.assertTrue(audit.verify())

    def test_production_change_is_gated(self):
        with self.assertRaises(GovernanceError):
            assert_execution_allowed(autonomy=3, risk="MEDIUM", production_change=True, approved=False)

    def test_confidence_policy(self):
        self.assertEqual(next_confidence_action(49), "DO_NOT_AUTONOMOUSLY_EXECUTE")
        self.assertEqual(next_confidence_action(90), "CONTROLLED_EXECUTION")

    def test_world_model_records_evidenced_dependency(self):
        with tempfile.TemporaryDirectory() as temp:
            model = WorldModel(Path(temp) / "world.db")
            product = model.add_entity("Product", "DhanSetuHub")
            provider = model.add_entity("PaymentProvider", "PayU")
            model.relate(product, "USES", provider, evidence="Architecture record AR-1", confidence=90)
            self.assertEqual(model.neighborhood(product)[0]["target_name"], "PayU")


if __name__ == "__main__":
    unittest.main()
