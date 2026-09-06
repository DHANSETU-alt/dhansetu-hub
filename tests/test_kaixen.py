import unittest
from unittest.mock import MagicMock, patch

from orchestrator import kaixen


class TestKaixen(unittest.TestCase):
    @patch("orchestrator.kaixen.db.log_bug_event")
    @patch("orchestrator.kaixen.db.insert_bug", return_value=41)
    @patch("orchestrator.kaixen.bug_fixer._describe_candidate", return_value="real traceback")
    @patch("orchestrator.kaixen.db.get_conn")
    @patch("orchestrator.kaixen.bug_fixer.scan_for_bugs")
    def test_triage_creates_traceable_ticket(self, scan, get_conn, describe, insert, event):
        candidate = {"source": "task_failure", "related_task_id": 7, "title": "Task #7 failed"}
        scan.return_value = [candidate]
        get_conn.return_value.__enter__.return_value = MagicMock()
        result = kaixen.triage_once()
        self.assertEqual(result["created"][0]["bug_id"], 41)
        self.assertEqual(insert.call_args.kwargs["severity"], "P1")
        self.assertIn("kaixen:task_failure", insert.call_args.kwargs["source"])
        event.assert_called_once()

    @patch("orchestrator.kaixen.bug_fixer.scan_for_bugs", return_value=[])
    def test_empty_scan_does_not_invent_work(self, _scan):
        self.assertEqual(kaixen.triage_once(), {"candidates": 0, "groups": 0, "created": [], "linked": []})


if __name__ == "__main__":
    unittest.main()
