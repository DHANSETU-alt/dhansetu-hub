import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import db, peopledesk


class TestPeopleDesk(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_peopledesk_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_add_staff_requires_wage_for_daily_pay_type(self):
        with self.assertRaises(ValueError):
            peopledesk.add_staff("owner@example.com", "Ramesh", pay_type="daily")

    def test_add_staff_requires_salary_for_monthly_pay_type(self):
        with self.assertRaises(ValueError):
            peopledesk.add_staff("owner@example.com", "Priya", pay_type="monthly")

    def test_add_staff_real_row(self):
        staff = peopledesk.add_staff("owner@example.com", "Ramesh", role="Operator",
                                      pay_type="daily", daily_wage_inr=500)
        self.assertEqual(staff["name"], "Ramesh")
        self.assertEqual(staff["daily_wage_inr"], 500)
        self.assertEqual(staff["status"], "active")

    def test_list_staff_scoped_to_owner_email(self):
        peopledesk.add_staff("owner1@example.com", "A", pay_type="daily", daily_wage_inr=100)
        peopledesk.add_staff("owner2@example.com", "B", pay_type="daily", daily_wage_inr=200)
        result = peopledesk.list_staff("owner1@example.com")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "A")

    def test_mark_attendance_rejects_unknown_staff(self):
        with self.assertRaises(ValueError):
            peopledesk.mark_attendance(999, "2026-08-25", "present")

    def test_mark_attendance_rejects_unknown_status(self):
        staff = peopledesk.add_staff("owner@example.com", "Ramesh", pay_type="daily", daily_wage_inr=500)
        with self.assertRaises(ValueError):
            peopledesk.mark_attendance(staff["id"], "2026-08-25", "on_vacation")

    def test_payroll_daily_wage_counts_present_and_half_days(self):
        staff = peopledesk.add_staff("owner@example.com", "Ramesh", pay_type="daily", daily_wage_inr=500)
        peopledesk.mark_attendance(staff["id"], "2026-08-01", "present")
        peopledesk.mark_attendance(staff["id"], "2026-08-02", "present")
        peopledesk.mark_attendance(staff["id"], "2026-08-03", "half_day")
        peopledesk.mark_attendance(staff["id"], "2026-08-04", "absent")

        summary = peopledesk.payroll_summary("owner@example.com", "2026-08-01", "2026-08-31")
        row = summary[0]
        self.assertEqual(row["present_days"], 2)
        self.assertEqual(row["half_days"], 1)
        self.assertEqual(row["absent_days"], 1)
        # 2 full days + 0.5 half day = 2.5 payable days x Rs.500
        self.assertEqual(row["payable_days"], 2.5)
        self.assertEqual(row["amount_inr"], 1250.0)

    def test_payroll_monthly_salary_ignores_attendance(self):
        staff = peopledesk.add_staff("owner@example.com", "Priya", pay_type="monthly", monthly_salary_inr=18000)
        peopledesk.mark_attendance(staff["id"], "2026-08-01", "absent")
        peopledesk.mark_attendance(staff["id"], "2026-08-02", "leave")

        summary = peopledesk.payroll_summary("owner@example.com", "2026-08-01", "2026-08-31")
        row = summary[0]
        self.assertIsNone(row["payable_days"])
        self.assertEqual(row["amount_inr"], 18000)

    def test_marking_attendance_twice_same_day_overwrites_not_duplicates(self):
        staff = peopledesk.add_staff("owner@example.com", "Ramesh", pay_type="daily", daily_wage_inr=500)
        peopledesk.mark_attendance(staff["id"], "2026-08-01", "present")
        peopledesk.mark_attendance(staff["id"], "2026-08-01", "absent")

        summary = peopledesk.payroll_summary("owner@example.com", "2026-08-01", "2026-08-31")
        row = summary[0]
        self.assertEqual(row["present_days"], 0)
        self.assertEqual(row["absent_days"], 1)


if __name__ == "__main__":
    unittest.main()
