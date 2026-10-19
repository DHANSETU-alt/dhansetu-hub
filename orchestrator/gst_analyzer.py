"""
GST LeakShield Analyzer
Analyzes business expenses for GST compliance, identifies under-reported GST,
and tracks input credit eligibility. Uses real 2024 GST rates.
"""

from dataclasses import dataclass
from typing import Dict, List
import json


@dataclass
class ExpenseEntry:
    """Represents a business expense for GST analysis."""
    category: str  # e.g., "supplies", "services", "travel"
    description: str
    amount: float
    has_gst_invoice: bool  # Whether proper GST invoice is available
    gst_paid: float  # GST actually paid (if any)


@dataclass
class GSTLeakFinding:
    """Identifies a potential GST leak."""
    category: str
    description: str
    expense_amount: float
    expected_gst_rate: float
    expected_gst_liability: float
    gst_reported: float
    leak_amount: float
    is_input_credit_eligible: bool
    recommendation: str


@dataclass
class GSTAuditReport:
    """Complete GST audit report."""
    total_expenses: float
    total_gst_liability: float
    total_gst_reported: float
    total_leak: float
    compliance_score: float  # 0-100
    findings: List[GSTLeakFinding]
    risk_level: str  # "low", "medium", "high", "critical"
    recommendations: List[str]


# GST Categories and Rates (India, April 2024)
GST_CATEGORIES = {
    # 5% GST Items
    "food_staples": {
        "rate": 0.05,
        "description": "Food staples, basic groceries",
        "input_credit": True,
    },
    "seeds": {
        "rate": 0.05,
        "description": "Seeds and planting materials",
        "input_credit": True,
    },
    "transport_passenger": {
        "rate": 0.05,
        "description": "Passenger transportation",
        "input_credit": False,
    },
    "health_services": {
        "rate": 0.05,
        "description": "Health services, medical consultation",
        "input_credit": False,
    },

    # 12% GST Items
    "office_supplies": {
        "rate": 0.12,
        "description": "Office supplies, stationery",
        "input_credit": True,
    },
    "cement": {
        "rate": 0.12,
        "description": "Cement and construction materials",
        "input_credit": True,
    },
    "leather": {
        "rate": 0.12,
        "description": "Leather goods",
        "input_credit": True,
    },
    "footwear": {
        "rate": 0.12,
        "description": "Footwear",
        "input_credit": True,
    },
    "software": {
        "rate": 0.12,
        "description": "Software, IT services",
        "input_credit": True,
    },
    "logistics": {
        "rate": 0.12,
        "description": "Logistics and warehousing",
        "input_credit": True,
    },
    "repairs_maintenance": {
        "rate": 0.12,
        "description": "Repairs and maintenance services",
        "input_credit": True,
    },
    "professional_fees": {
        "rate": 0.12,
        "description": "Professional services (CA, lawyer, consultant)",
        "input_credit": True,
    },

    # 18% GST Items (most services and goods)
    "general_services": {
        "rate": 0.18,
        "description": "General services, consulting, advertising",
        "input_credit": True,
    },
    "restaurant": {
        "rate": 0.18,
        "description": "Restaurant and catering",
        "input_credit": False,  # Food items generally no input credit
    },
    "hotel": {
        "rate": 0.18,
        "description": "Hotel accommodation",
        "input_credit": True,
    },
    "vehicle_purchase": {
        "rate": 0.18,
        "description": "Vehicle purchase",
        "input_credit": True,
    },
    "fuel": {
        "rate": 0.18,
        "description": "Fuel and petroleum products",
        "input_credit": False,  # Motor spirits have special rules
    },
    "internet_telecom": {
        "rate": 0.18,
        "description": "Internet, telecommunications",
        "input_credit": True,
    },
    "electricity": {
        "rate": 0.18,
        "description": "Electricity and power",
        "input_credit": True,
    },
    "accommodation": {
        "rate": 0.18,
        "description": "Accommodation and stay",
        "input_credit": True,
    },

    # 28% GST Items (luxury goods)
    "luxury_vehicles": {
        "rate": 0.28,
        "description": "Luxury vehicles",
        "input_credit": True,
    },
    "precious_metals": {
        "rate": 0.28,
        "description": "Precious metals and gems",
        "input_credit": True,
    },
    "aeroplane": {
        "rate": 0.28,
        "description": "Aircraft and aviation",
        "input_credit": True,
    },

    # 0% GST (Exempt or Zero-rated)
    "export": {
        "rate": 0.00,
        "description": "Export of goods/services",
        "input_credit": True,
    },
    "fertilizers": {
        "rate": 0.00,
        "description": "Fertilizers",
        "input_credit": True,
    },
}

# Common compliance gaps
COMMON_GAPS = {
    "missing_invoice": "No proper GST invoice - input credit not available",
    "wrong_rate": "Incorrect GST rate applied",
    "blocked_credit": "GST paid on non-deductible items (e.g., personal use)",
    "cash_transaction": "Cash transaction without GST documentation",
    "wrong_category": "Expense categorized incorrectly for GST purposes",
    "input_not_used": "Input GST but item cannot be used for business purposes",
}


def analyze_gst_compliance(expenses: List[ExpenseEntry]) -> GSTAuditReport:
    """
    Analyze GST compliance across all expenses.
    Identifies gaps and calculates GST liability vs reported.
    """
    findings = []
    total_expenses = 0.0
    total_gst_liability = 0.0
    total_gst_reported = 0.0
    total_leak = 0.0

    for expense in expenses:
        total_expenses += expense.amount

        # Get GST category info
        category_info = GST_CATEGORIES.get(
            expense.category,
            {
                "rate": 0.18,
                "description": "Unknown category (assumed 18%)",
                "input_credit": True,
            },
        )

        gst_rate = category_info["rate"]
        expected_gst = expense.amount * gst_rate
        is_credit_eligible = category_info["input_credit"]

        total_gst_liability += expected_gst
        total_gst_reported += expense.gst_paid

        # Identify leak
        leak = expected_gst - expense.gst_paid
        total_leak += leak

        if leak > 0 or not expense.has_gst_invoice:
            # Only report findings if there's a gap
            if not expense.has_gst_invoice:
                recommendation = "Obtain proper GST invoice for input credit eligibility"
                leak_amount = expected_gst if is_credit_eligible else 0.0
            elif leak > 0:
                recommendation = f"GST gap of ₹{leak:,.0f} - verify GST rate and documentation"
                leak_amount = leak
            else:
                recommendation = "Review GST documentation"
                leak_amount = 0.0

            findings.append(
                GSTLeakFinding(
                    category=expense.category,
                    description=expense.description,
                    expense_amount=expense.amount,
                    expected_gst_rate=gst_rate,
                    expected_gst_liability=expected_gst,
                    gst_reported=expense.gst_paid,
                    leak_amount=leak_amount,
                    is_input_credit_eligible=is_credit_eligible,
                    recommendation=recommendation,
                )
            )

    # Calculate compliance score
    if total_gst_liability > 0:
        compliance_score = max(
            0, (1 - (total_leak / total_gst_liability)) * 100
        )
    else:
        compliance_score = 100.0

    # Determine risk level
    if compliance_score >= 95:
        risk_level = "low"
    elif compliance_score >= 85:
        risk_level = "medium"
    elif compliance_score >= 70:
        risk_level = "high"
    else:
        risk_level = "critical"

    # Generate recommendations
    recommendations = []
    if total_leak > 0:
        recommendations.append(
            f"Total GST leak: ₹{total_leak:,.0f} - address compliance gaps urgently"
        )
    if not all(e.has_gst_invoice for e in expenses):
        recommendations.append("Maintain proper GST invoices for all business purchases")
    if len(findings) > 0:
        recommendations.append(
            f"Review {len(findings)} expense(s) with GST compliance issues"
        )
    if not recommendations:
        recommendations.append("GST compliance is strong - continue current practices")

    return GSTAuditReport(
        total_expenses=total_expenses,
        total_gst_liability=total_gst_liability,
        total_gst_reported=total_gst_reported,
        total_leak=total_leak,
        compliance_score=compliance_score,
        findings=findings,
        risk_level=risk_level,
        recommendations=recommendations,
    )


def categorize_expense(description: str, amount: float) -> str:
    """
    Auto-categorize an expense based on description.
    Uses keyword matching.
    """
    description_lower = description.lower()

    # Simple keyword-based categorization
    category_keywords = {
        "office_supplies": ["stationery", "supplies", "office", "pen", "paper"],
        "software": ["software", "subscription", "saas", "license", "tool"],
        "professional_fees": ["consultant", "lawyer", "ca", "chartered accountant", "fees"],
        "internet_telecom": ["internet", "broadband", "phone", "mobile", "telecom"],
        "electricity": ["electricity", "power", "light", "bills"],
        "repair_maintenance": ["repair", "maintenance", "service", "fix"],
        "travel": ["travel", "flight", "hotel", "accommodation", "transport"],
        "general_services": ["service", "consulting", "advice", "support"],
    }

    for category, keywords in category_keywords.items():
        if any(keyword in description_lower for keyword in keywords):
            return category

    # Default to general services
    return "general_services"


def format_finding_for_json(finding: GSTLeakFinding) -> Dict:
    """Format a finding for JSON serialization."""
    return {
        "category": finding.category,
        "description": finding.description,
        "expense_amount": round(finding.expense_amount, 2),
        "expected_gst_rate": f"{finding.expected_gst_rate * 100:.0f}%",
        "expected_gst_liability": round(finding.expected_gst_liability, 2),
        "gst_reported": round(finding.gst_reported, 2),
        "leak_amount": round(finding.leak_amount, 2),
        "is_input_credit_eligible": finding.is_input_credit_eligible,
        "recommendation": finding.recommendation,
    }


def format_report_for_json(report: GSTAuditReport) -> Dict:
    """Format a report for JSON serialization."""
    return {
        "total_expenses": round(report.total_expenses, 2),
        "total_gst_liability": round(report.total_gst_liability, 2),
        "total_gst_reported": round(report.total_gst_reported, 2),
        "total_leak": round(report.total_leak, 2),
        "compliance_score": round(report.compliance_score, 2),
        "risk_level": report.risk_level,
        "findings": [format_finding_for_json(f) for f in report.findings],
        "recommendations": report.recommendations,
    }


# Test cases
if __name__ == "__main__":
    # Test: ₹10L business expenses with GST analysis
    print("Test: ₹10L business expenses with GST analysis")
    expenses = [
        ExpenseEntry("office_supplies", "Stationery and office materials", 50000, True, 6000),
        ExpenseEntry("software", "SaaS subscription (annual)", 120000, True, 14400),  # Should be 21600
        ExpenseEntry("professional_fees", "Chartered Accountant fees", 75000, True, 9000),  # Should be 9000
        ExpenseEntry("internet_telecom", "Internet and telecom", 36000, True, 6480),  # Should be 6480
        ExpenseEntry("electricity", "Electricity bills", 48000, True, 8640),  # Should be 8640
        ExpenseEntry("travel", "Business travel", 200000, False, 0),  # No invoice - can't claim credit
        ExpenseEntry("general_services", "Consulting services", 300000, True, 40000),  # Should be 54000
        ExpenseEntry("restaurant", "Client meals", 95000, False, 0),  # No input credit for restaurant
    ]

    report = analyze_gst_compliance(expenses)
    result = format_report_for_json(report)
    print(json.dumps(result, indent=2))
