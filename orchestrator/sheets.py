"""
Google Sheets — the official business ledger. 8 tabs, accountant-readable,
append-only. Derived columns (profit, margin, tax, cash flow) are computed
in Python via calculations.py and written as plain values, not live
spreadsheet formulas -- values.append doesn't report which row a batch
lands on ahead of time, so a self-referencing formula has nothing reliable
to point at for a sheet that grows one row per sync. The tradeoff: edit a
raw number by hand in the sheet and the derived columns on that row won't
recompute -- re-run the sync (or fix the source data and resync) instead.

Credentials: manual entry, same as Telegram -- a service-account JSON key
path and a spreadsheet ID, passed explicitly every call, never read from a
stored config file. See README "Google Sheets setup" for how to create
the service account and share the sheet with it.

Sync strategy per tab:
  - Ledgers (Revenue, Expense, AI Cost, CEO Decision Log): append-only,
    new rows since a locally-tracked cursor (.sheets_sync_state.json) --
    idempotent, safe to re-run, never rewrites history.
  - Snapshot sheets (Daily Summary, P&L, Tax Register, Website Health):
    append one freshly-computed row per business per sync run.

This module has NOT been exercised against a live spreadsheet in this
session -- no credentials were available to test with. The row-building
logic is covered by tests/test_calculations.py without needing live
credentials; the actual API calls (ensure_structure, the sync_* writes)
are real, correct calls against the documented Sheets API v4 shape, but
unverified end-to-end. Run --sheets-sync once you have a service account
and treat the first run as the verification step.
"""
import json
import os
from datetime import date
from pathlib import Path

from . import calculations as calc
from . import config, db, finance

SHEET_NAMES = [
    "Daily Summary",
    "Revenue Ledger",
    "Expense Ledger",
    "P&L Statement",
    "Tax Register",
    "AI Cost Ledger",
    "Website Health",
    "CEO Decision Log",
    "Audit History",
    "System Health",
    "Security History",
    "Correction History",
]

HEADERS = {
    "Daily Summary": ["Date", "Business", "Revenue", "Expenses", "AI Cost", "Profit", "Operating Margin %", "Cash Flow", "Active Tasks"],
    "Revenue Ledger": ["Entry ID", "Date", "Business", "Amount", "Description"],
    "Expense Ledger": ["Entry ID", "Date", "Business", "Category", "Amount", "Description"],
    "P&L Statement": ["Period", "Business", "Revenue", "AI Cost", "Operating Expenses", "Net Profit", "Operating Margin %",
                       "Estimated Tax", "Net Profit After Tax"],
    "Tax Register": ["Period", "Business", "Taxable Profit", "Tax Rate %", "Estimated Tax", "Notes"],
    "AI Cost Ledger": ["Cost ID", "Date", "Provider", "Model", "Tokens In", "Tokens Out", "Cost USD"],
    "Website Health": ["Date", "Business", "Domain", "Template", "Status", "File Present"],
    "CEO Decision Log": ["Decision ID", "Date", "Business", "Goal", "Status", "Priority", "Risk", "Business Impact", "Reason"],
    "Audit History": ["Audit ID", "Date", "Files Scanned", "Findings", "Severity Score", "Files Affected",
                       "Deepened Bug IDs", "Executive Summary"],
    "System Health": ["Snapshot ID", "Date", "Health Score", "Performance Score", "CPU %", "RAM %",
                       "Disk %", "Internet", "Ollama", "Database"],
    "Security History": ["Report ID", "Date", "Business", "Score", "Findings Count"],
    "Correction History": ["Correction ID", "Date", "Task Type", "Task Ref", "Correction Score", "Quality Score",
                            "Issues Found", "Issues Fixed", "Final Status", "Summary"],
}

DEFAULT_TAX_RATE = float(os.environ.get("SHAKTHI_DEFAULT_TAX_RATE", "0.18"))  # GST-style default; override per call
STATE_PATH = config.ROOT / ".sheets_sync_state.json"


class SheetsError(RuntimeError):
    pass


def get_client(credentials_path: str):
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as e:
        raise SheetsError(
            "google-api-python-client / google-auth not installed. "
            "Run: pip install google-api-python-client google-auth google-auth-httplib2"
        ) from e

    if not credentials_path or not Path(credentials_path).exists():
        raise SheetsError(f"service account credentials file not found: {credentials_path!r}")

    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds)


def _load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def _save_state(state: dict):
    STATE_PATH.write_text(json.dumps(state, indent=2))


def ensure_structure(client, spreadsheet_id: str):
    """Create any missing tabs and (re)write header rows. Safe to call
    every sync -- addSheet is skipped for tabs that already exist."""
    meta = client.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing = {s["properties"]["title"] for s in meta.get("sheets", [])}

    missing = [name for name in SHEET_NAMES if name not in existing]
    if missing:
        requests = [{"addSheet": {"properties": {"title": name}}} for name in missing]
        client.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests}).execute()

    for name in SHEET_NAMES:
        client.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{name}'!A1",
            valueInputOption="RAW",
            body={"values": [HEADERS[name]]},
        ).execute()


def read_values(client, spreadsheet_id: str, range_a1: str) -> list:
    """Real read call against the documented Sheets API v4 values.get shape
    -- same "not yet exercised against a live spreadsheet" caveat as the
    rest of this module (see module docstring): no service account was
    available to test with this session. Used by dhansetu_ai.py to pull
    course titles from the founder's own sheet; range_a1 e.g. "'Courses'!A2:A".
    """
    result = client.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_a1).execute()
    return result.get("values", [])


def read_course_titles(client, spreadsheet_id: str, sheet_name: str = "Courses") -> list:
    """One title per non-empty row in column A, header row skipped (starts
    at row 2). Returns real titles only -- blank rows in the middle of the
    sheet are dropped, not turned into empty-string course entries."""
    rows = read_values(client, spreadsheet_id, f"'{sheet_name}'!A2:A")
    return [row[0].strip() for row in rows if row and row[0].strip()]


def _append(client, spreadsheet_id: str, sheet: str, rows: list):
    if not rows:
        return 0
    client.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet}'!A1",
        valueInputOption="USER_ENTERED",  # so formula strings actually evaluate
        insertDataOption="INSERT_ROWS",
        body={"values": rows},
    ).execute()
    return len(rows)


def sync_revenue_and_expense_ledgers(client, spreadsheet_id: str, state: dict) -> dict:
    with db.get_conn() as conn:
        new_revenue = db.list_finance_entries(conn, since_id=state.get("revenue_ledger_last_id", 0), type_="revenue")
        new_expense = db.list_finance_entries(conn, since_id=state.get("expense_ledger_last_id", 0), type_="expense")
        businesses = {b["id"]: b["name"] for b in db.list_businesses(conn)}

    rev_rows = [[e["id"], e["created_at"], businesses.get(e["business_id"], "?"), e["amount"], e["description"]] for e in new_revenue]
    exp_rows = [[e["id"], e["created_at"], businesses.get(e["business_id"], "?"), e["category"], e["amount"], e["description"]]
                for e in new_expense]

    _append(client, spreadsheet_id, "Revenue Ledger", rev_rows)
    _append(client, spreadsheet_id, "Expense Ledger", exp_rows)

    if new_revenue:
        state["revenue_ledger_last_id"] = max(e["id"] for e in new_revenue)
    if new_expense:
        state["expense_ledger_last_id"] = max(e["id"] for e in new_expense)
    return {"revenue_rows": len(rev_rows), "expense_rows": len(exp_rows)}


def sync_ai_cost_ledger(client, spreadsheet_id: str, state: dict) -> dict:
    with db.get_conn() as conn:
        new_costs = db.cost_ledger_since(conn, since_id=state.get("ai_cost_ledger_last_id", 0))
    rows = [[c["id"], c["created_at"], c["provider"], c["model"], c["tokens_in"], c["tokens_out"], c["cost_usd"]] for c in new_costs]
    _append(client, spreadsheet_id, "AI Cost Ledger", rows)
    if new_costs:
        state["ai_cost_ledger_last_id"] = max(c["id"] for c in new_costs)
    return {"rows": len(rows)}


def sync_ceo_decision_log(client, spreadsheet_id: str, state: dict) -> dict:
    with db.get_conn() as conn:
        new_decisions = db.decisions_since(conn, since_id=state.get("ceo_log_last_id", 0))
        businesses = {b["id"]: b["name"] for b in db.list_businesses(conn)}
    rows = [[
        d["id"], d["created_at"], businesses.get(d["business_id"], "?") if d["business_id"] else "(cross-business)",
        d["goal"], d["status"], d["priority_score"], d["risk_score"], d["business_impact_score"], d["reason"],
    ] for d in new_decisions]
    _append(client, spreadsheet_id, "CEO Decision Log", rows)
    if new_decisions:
        state["ceo_log_last_id"] = max(d["id"] for d in new_decisions)
    return {"rows": len(rows)}


def sync_daily_summary(client, spreadsheet_id: str) -> dict:
    """Plain computed values, not live formulas: `values.append` doesn't
    report which row it landed on ahead of time, and this sheet appends one
    row per business per sync -- there's no fixed row a self-referencing
    formula could reliably target. (P&L Statement below has the same
    constraint for the same reason; Tax Register too.)"""
    with db.get_conn() as conn:
        businesses = db.list_businesses(conn)
        active_tasks = db.active_task_count(conn)
    today = date.today().isoformat()
    rows = []
    for b in businesses:
        r = finance.generate_report("daily", business_id=b["id"])
        p = calc.profit(r["revenue_usd"], r["expense_usd"], r["api_cost_usd"])
        margin = calc.operating_margin(r["revenue_usd"], p)
        cf = calc.cash_flow(r["revenue_usd"], r["expense_usd"])
        rows.append([today, b["name"], r["revenue_usd"], r["expense_usd"], r["api_cost_usd"],
                     round(p, 2), round(margin * 100, 2), round(cf, 2), active_tasks])
    _append(client, spreadsheet_id, "Daily Summary", rows)
    return {"rows": len(rows)}


def sync_pl_and_tax(client, spreadsheet_id: str, period: str, tax_rate: float = DEFAULT_TAX_RATE) -> dict:
    with db.get_conn() as conn:
        businesses = db.list_businesses(conn)
    pl_rows, tax_rows = [], []
    for b in businesses:
        r = finance.generate_report(period, business_id=b["id"])
        p = calc.profit(r["revenue_usd"], r["expense_usd"], r["api_cost_usd"])
        margin = calc.operating_margin(r["revenue_usd"], p)
        tax = calc.estimated_tax(p, tax_rate)
        after_tax = calc.net_profit_after_tax(p, tax)
        pl_rows.append([period, b["name"], r["revenue_usd"], r["api_cost_usd"], r["expense_usd"],
                         round(p, 2), round(margin * 100, 2), round(tax, 2), round(after_tax, 2)])
        tax_rows.append([period, b["name"], round(p, 2), round(tax_rate * 100, 2), round(tax, 2),
                          "estimate only -- not a filed calculation, confirm with an accountant"])
    _append(client, spreadsheet_id, "P&L Statement", pl_rows)
    _append(client, spreadsheet_id, "Tax Register", tax_rows)
    return {"pl_rows": len(pl_rows), "tax_rows": len(tax_rows)}


def sync_website_health(client, spreadsheet_id: str) -> dict:
    with db.get_conn() as conn:
        sites = conn.execute("SELECT * FROM sites WHERE status != 'planned'").fetchall()
        sites = [dict(s) for s in sites]
        businesses = {b["id"]: b["name"] for b in db.list_businesses(conn)}
    today = date.today().isoformat()
    rows = []
    for s in sites:
        exists = bool(s["local_path"] and Path(s["local_path"]).exists())
        rows.append([today, businesses.get(s["business_id"], "?"), s["domain"], s["template_id"], s["status"], exists])
    _append(client, spreadsheet_id, "Website Health", rows)
    return {"rows": len(rows)}


def sync_audit_history(client, spreadsheet_id: str, state: dict) -> dict:
    with db.get_conn() as conn:
        audits = conn.execute(
            "SELECT * FROM audits WHERE id > ? AND status = 'completed' ORDER BY id",
            (state.get("audit_history_last_id", 0),),
        ).fetchall()
        audits = [dict(a) for a in audits]

    rows = []
    for a in audits:
        with db.get_conn() as conn:
            bug_findings = conn.execute(
                "SELECT bug_id FROM audit_findings WHERE audit_id = ? AND bug_id IS NOT NULL", (a["id"],)
            ).fetchall()
        deepened = ",".join(str(r["bug_id"]) for r in bug_findings) or "(none)"
        rows.append([a["id"], a["completed_at"], a["files_affected"], a["findings_count"],
                     a["severity_score"], a["files_affected"], deepened, a["executive_summary"] or ""])

    _append(client, spreadsheet_id, "Audit History", rows)
    if audits:
        state["audit_history_last_id"] = max(a["id"] for a in audits)
    return {"rows": len(rows)}


def sync_system_health(client, spreadsheet_id: str, state: dict) -> dict:
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM system_health WHERE id > ? ORDER BY id", (state.get("system_health_last_id", 0),)
        ).fetchall()
        rows = [dict(r) for r in rows]
    sheet_rows = [[r["id"], r["created_at"], r["health_score"], r["performance_score"], r["cpu_percent"],
                   r["ram_percent"], r["disk_percent"], bool(r["internet_ok"]), bool(r["ollama_ok"]), bool(r["db_ok"])]
                  for r in rows]
    _append(client, spreadsheet_id, "System Health", sheet_rows)
    if rows:
        state["system_health_last_id"] = max(r["id"] for r in rows)
    return {"rows": len(sheet_rows)}


def sync_security_history(client, spreadsheet_id: str, state: dict) -> dict:
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM security_reports WHERE id > ? ORDER BY id", (state.get("security_history_last_id", 0),)
        ).fetchall()
        rows = [dict(r) for r in rows]
        businesses = {b["id"]: b["name"] for b in db.list_businesses(conn)}
    sheet_rows = [[r["id"], r["created_at"], businesses.get(r["business_id"], "(all)") if r["business_id"] else "(all)",
                   r["score"], len(json.loads(r["findings"]))] for r in rows]
    _append(client, spreadsheet_id, "Security History", sheet_rows)
    if rows:
        state["security_history_last_id"] = max(r["id"] for r in rows)
    return {"rows": len(sheet_rows)}


def sync_correction_history(client, spreadsheet_id: str, state: dict) -> dict:
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM corrections WHERE id > ? AND status = 'completed' ORDER BY id",
            (state.get("correction_history_last_id", 0),),
        ).fetchall()
        rows = [dict(r) for r in rows]
    sheet_rows = [[r["id"], r["completed_at"], r["task_type"], r["task_ref"] or "", r["correction_score"],
                   r["quality_score"], r["issues_found"], r["issues_fixed"], r["final_status"], r["summary"] or ""]
                  for r in rows]
    _append(client, spreadsheet_id, "Correction History", sheet_rows)
    if rows:
        state["correction_history_last_id"] = max(r["id"] for r in rows)
    return {"rows": len(sheet_rows)}


def sync_all(credentials_path: str, spreadsheet_id: str, period: str = "monthly", tax_rate: float = DEFAULT_TAX_RATE) -> dict:
    client = get_client(credentials_path)
    ensure_structure(client, spreadsheet_id)

    state = _load_state()
    results = {}
    results["revenue_expense"] = sync_revenue_and_expense_ledgers(client, spreadsheet_id, state)
    results["ai_cost"] = sync_ai_cost_ledger(client, spreadsheet_id, state)
    results["ceo_log"] = sync_ceo_decision_log(client, spreadsheet_id, state)
    results["daily_summary"] = sync_daily_summary(client, spreadsheet_id)
    results["pl_tax"] = sync_pl_and_tax(client, spreadsheet_id, period, tax_rate)
    results["website_health"] = sync_website_health(client, spreadsheet_id)
    results["audit_history"] = sync_audit_history(client, spreadsheet_id, state)
    results["system_health"] = sync_system_health(client, spreadsheet_id, state)
    results["security_history"] = sync_security_history(client, spreadsheet_id, state)
    results["correction_history"] = sync_correction_history(client, spreadsheet_id, state)
    _save_state(state)

    return results
