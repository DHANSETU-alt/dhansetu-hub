"""
Dhansetu PeopleDesk -- a real staff/attendance/payroll tool for local small
businesses and small industrial units. Real launch scope, deliberately
lean (matches PDF Studio's own restraint): a staff directory, daily
attendance, and a deterministic payroll summary computed from real
attendance x wage. No leave policy engine, no tax/statutory compliance, no
payslip generation -- those are real, separate features, not implied by
"ready" here.

Same no-real-auth model as PDF Studio: owner_email is the only identity
concept. The pricing gate (free_uses=0, see pricing.PRODUCT_PRICING) is
enforced by the caller (the API route), not here -- same layering PDF
Studio's process route already uses.
"""
from . import db


def add_staff(owner_email: str, name: str, role: str = "", phone: str = "",
              pay_type: str = "daily", daily_wage_inr: float = None,
              monthly_salary_inr: float = None, join_date: str = "") -> dict:
    if pay_type not in ("daily", "monthly"):
        raise ValueError("pay_type must be 'daily' or 'monthly'")
    if pay_type == "daily" and not daily_wage_inr:
        raise ValueError("daily_wage_inr is required when pay_type is 'daily'")
    if pay_type == "monthly" and not monthly_salary_inr:
        raise ValueError("monthly_salary_inr is required when pay_type is 'monthly'")

    with db.get_conn() as conn:
        staff_id = db.insert_staff(conn, owner_email, name, role, phone, pay_type,
                                    daily_wage_inr, monthly_salary_inr, join_date)
        return db.get_staff(conn, staff_id)


def list_staff(owner_email: str, status: str = "active") -> list:
    with db.get_conn() as conn:
        return db.list_staff(conn, owner_email, status=status)


def mark_attendance(staff_id: int, attendance_date: str, status: str) -> None:
    if status not in ("present", "absent", "half_day", "leave"):
        raise ValueError("status must be present|absent|half_day|leave")
    with db.get_conn() as conn:
        if not db.get_staff(conn, staff_id):
            raise ValueError(f"no staff member with id {staff_id}")
        db.mark_attendance(conn, staff_id, attendance_date, status)


def payroll_summary(owner_email: str, date_from: str, date_to: str) -> list:
    """Deterministic, real math -- no invented numbers. Daily-wage staff:
    (present days + half_day days x 0.5) x daily_wage. Monthly-salary
    staff: the flat monthly_salary, regardless of attendance -- that's
    what a monthly salary means; docking pay for absence is a real,
    separate policy this MVP doesn't implement."""
    with db.get_conn() as conn:
        staff = db.list_staff(conn, owner_email, status="active")
        attendance = db.attendance_for_range(conn, owner_email, date_from, date_to)

    by_staff = {}
    for a in attendance:
        by_staff.setdefault(a["staff_id"], []).append(a)

    summary = []
    for s in staff:
        records = by_staff.get(s["id"], [])
        present_days = sum(1 for r in records if r["status"] == "present")
        half_days = sum(1 for r in records if r["status"] == "half_day")
        absent_days = sum(1 for r in records if r["status"] == "absent")
        leave_days = sum(1 for r in records if r["status"] == "leave")

        if s["pay_type"] == "daily":
            payable_days = present_days + (half_days * 0.5)
            amount = round(payable_days * (s["daily_wage_inr"] or 0), 2)
        else:
            payable_days = None
            amount = s["monthly_salary_inr"] or 0

        summary.append({
            "staff_id": s["id"], "name": s["name"], "pay_type": s["pay_type"],
            "present_days": present_days, "half_days": half_days,
            "absent_days": absent_days, "leave_days": leave_days,
            "payable_days": payable_days, "amount_inr": amount,
        })
    return summary
