"""
Finance reporting. Pulls real numbers from cost_ledger and finance_entries --
there is no live billing integration, so revenue/expense are whatever has
been logged via db.insert_finance_entry (founder input via CLI, or a task
routed through the Finance agent). Also computes actual Ollama savings: what
the tokens spent on local calls would have cost had they gone to Claude
instead, using the same cost model the escalation path already uses.
"""
from datetime import datetime, timedelta

from . import db, model_gateway

PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30, "quarterly": 90, "yearly": 365}


def _since(period: str) -> str:
    days = PERIOD_DAYS.get(period)
    if days is None:
        raise ValueError(f"period must be one of {list(PERIOD_DAYS)}")
    cutoff = datetime.utcnow() - timedelta(days=days)
    return cutoff.strftime("%Y-%m-%d %H:%M:%S")


def generate_report(period: str = "daily", business_id: int | None = None) -> dict:
    since = _since(period)

    with db.get_conn() as conn:
        cost_rows = db.cost_summary(conn, since=since)
        finance_rows = db.finance_entries_summary(conn, business_id=business_id, since=since)

    ollama_tokens_in = sum(r["tokens_in"] or 0 for r in cost_rows if r["provider"] == "ollama")
    ollama_tokens_out = sum(r["tokens_out"] or 0 for r in cost_rows if r["provider"] == "ollama")
    ollama_calls = sum(r["calls"] or 0 for r in cost_rows if r["provider"] == "ollama")
    claude_cost = sum(r["cost_usd"] or 0.0 for r in cost_rows if r["provider"] == "claude")

    # Actual local cost is $0 -- this is what running those same calls
    # through Claude instead would have cost, i.e. the real savings figure.
    estimated_savings = model_gateway.estimate_cloud_cost(ollama_tokens_in, ollama_tokens_out)

    revenue = sum(r["total"] for r in finance_rows if r["type"] == "revenue")
    expense = sum(r["total"] for r in finance_rows if r["type"] == "expense")

    return {
        "period": period,
        "since": since,
        "business_id": business_id,
        "api_cost_usd": round(claude_cost, 4),
        "ollama_calls": ollama_calls,
        "ollama_estimated_savings_usd": round(estimated_savings, 4),
        "revenue_usd": round(revenue, 2),
        "expense_usd": round(expense, 2),
        "profit_usd": round(revenue - expense - claude_cost, 2),
        "cost_by_provider": cost_rows,
    }
