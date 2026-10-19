"""
Accounting calculations, kept as pure functions with no DB/API dependency
-- fully unit-testable offline, independent of whether Google Sheets
credentials exist. sheets.py calls these; it never computes inline.

Honesty notes, not hedging:
- cash_flow here is revenue - expenses with no AR/AP timing (no invoices,
  no payment-due tracking exist in this system) -- a real cash-flow
  statement needs receivables/payables data this system doesn't capture.
  Treat it as a same-period proxy, not a cash-basis statement.
- estimated_tax is profit * a rate you provide. It is NOT a filed tax
  calculation, has no jurisdiction logic, and does not know about
  deductions, slabs, or GST input credits. It exists so the sheet has a
  number to review with an actual accountant, not to replace one.
"""


def profit(revenue: float, expenses: float, ai_cost: float = 0.0) -> float:
    return revenue - expenses - ai_cost


def operating_margin(revenue: float, net_profit: float) -> float:
    """Returns a fraction (0.25 == 25%), not a percentage."""
    if revenue == 0:
        return 0.0
    return net_profit / revenue


def cash_flow(revenue: float, expenses: float) -> float:
    return revenue - expenses


def estimated_tax(taxable_profit: float, tax_rate: float) -> float:
    """tax_rate as a fraction (0.18 for 18% GST-equivalent, 0.25 for a
    25% income tax estimate, etc.) -- caller decides the rate; this
    function has no jurisdiction-specific logic."""
    return max(0.0, taxable_profit) * tax_rate


def roi(revenue: float, total_cost: float) -> float:
    """Returns a fraction. total_cost = expenses + ai_cost (all-in cost)."""
    if total_cost == 0:
        return 0.0
    return (revenue - total_cost) / total_cost


def net_profit_after_tax(net_profit: float, tax: float) -> float:
    return net_profit - tax
