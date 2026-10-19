"""
Real tests for the daily team work register -- attendance, hours, work
assigned/done for the real human team (engineers/staff). Purely
deterministic, no model calls to mock, unlike sales.py/marketing.py.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import db, team_register


class TeamRegisterTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_team_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestAddWorker(TeamRegisterTestBase):
    def test_creates_a_real_worker_row(self):
        worker_id = team_register.add_worker(None, "Ramesh Kumar", role="mason", contact="9876543210")
        workers = team_register.list_workers()
        self.assertEqual(len(workers), 1)
        self.assertEqual(workers[0]["id"], worker_id)
        self.assertEqual(workers[0]["role"], "mason")
        self.assertEqual(workers[0]["status"], "active")


class TestLogDay(TeamRegisterTestBase):
    def test_log_present_day_with_hours(self):
        worker_id = team_register.add_worker(None, "Ramesh Kumar")
        entry = team_register.log_day(worker_id, "2026-08-24", present=True, hours_worked=8,
                                        work_assigned="Lay bricks", work_done="East wall done")
        self.assertEqual(entry["present"], 1)
        self.assertEqual(entry["hours_worked"], 8)
        self.assertEqual(entry["work_done"], "East wall done")

    def test_log_absent_day(self):
        worker_id = team_register.add_worker(None, "Suresh Yadav")
        entry = team_register.log_day(worker_id, "2026-08-24", present=False, notes="sick leave")
        self.assertEqual(entry["present"], 0)
        self.assertIsNone(entry["hours_worked"])

    def test_second_call_same_day_corrects_not_duplicates(self):
        """The core one-entry-per-day behavior: one real entry per worker per
        day, a re-log overwrites it (same as crossing out a line and
        rewriting), it never creates a second row."""
        worker_id = team_register.add_worker(None, "Ramesh Kumar")
        first = team_register.log_day(worker_id, "2026-08-24", present=True, hours_worked=8)
        second = team_register.log_day(worker_id, "2026-08-24", present=True, hours_worked=9)

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["hours_worked"], 9)

        history = team_register.worker_history(worker_id)
        self.assertEqual(len(history), 1)

    def test_raises_for_unknown_worker(self):
        with self.assertRaises(ValueError):
            team_register.log_day(9999, "2026-08-24", present=True)


class TestDailySummary(TeamRegisterTestBase):
    def test_counts_present_absent_and_surfaces_not_logged(self):
        w1 = team_register.add_worker(None, "Ramesh Kumar")
        w2 = team_register.add_worker(None, "Suresh Yadav")
        w3 = team_register.add_worker(None, "Vikram Singh")  # never logged

        team_register.log_day(w1, "2026-08-24", present=True, hours_worked=9)
        team_register.log_day(w2, "2026-08-24", present=False)

        summary = team_register.daily_summary("2026-08-24")

        self.assertEqual(summary["present_count"], 1)
        self.assertEqual(summary["absent_count"], 1)
        self.assertEqual(summary["total_hours"], 9)
        self.assertEqual(len(summary["not_logged"]), 1)
        self.assertEqual(summary["not_logged"][0]["id"], w3)

    def test_absent_hours_never_counted(self):
        w1 = team_register.add_worker(None, "Someone")
        team_register.log_day(w1, "2026-08-24", present=False, hours_worked=None)
        summary = team_register.daily_summary("2026-08-24")
        self.assertEqual(summary["total_hours"], 0)


class TestWorkerSummary(TeamRegisterTestBase):
    def test_rollup_across_multiple_days(self):
        worker_id = team_register.add_worker(None, "Ramesh Kumar")
        team_register.log_day(worker_id, "2026-08-22", present=True, hours_worked=8)
        team_register.log_day(worker_id, "2026-08-23", present=False)
        team_register.log_day(worker_id, "2026-08-24", present=True, hours_worked=9)

        summary = team_register.worker_summary(worker_id)

        self.assertEqual(summary["days_logged"], 3)
        self.assertEqual(summary["days_present"], 2)
        self.assertEqual(summary["days_absent"], 1)
        self.assertEqual(summary["total_hours"], 17)

    def test_date_range_filter(self):
        worker_id = team_register.add_worker(None, "Ramesh Kumar")
        team_register.log_day(worker_id, "2026-08-01", present=True, hours_worked=8)
        team_register.log_day(worker_id, "2026-08-24", present=True, hours_worked=9)

        summary = team_register.worker_summary(worker_id, date_from="2026-08-20", date_to="2026-08-31")
        self.assertEqual(summary["days_logged"], 1)
        self.assertEqual(summary["total_hours"], 9)


if __name__ == "__main__":
    unittest.main()
