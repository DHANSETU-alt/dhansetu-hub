"""
Indian Tax Estimator Engine
Handles old regime (slabs), new regime (flat slabs), deductions, credits, and recommendations.
Uses 2024-2025 FY tax rates per Indian Income Tax Act.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import json


@dataclass
class TaxDeduction:
    """Represents a tax deduction with category and amount."""
    category: str  # e.g., "80C", "80D", "Other"
    description: str  # e.g., "Medical Insurance Premium"
    amount: float


@dataclass
class TaxCalculationResult:
    """Result of a single tax calculation."""
    regime: str  # "old" or "new"
    gross_income: float
    taxable_income: float
    total_tax: float
    cess: float  # 4% health and education cess
    total_liability: float
    deductions_applied: List[Dict]
    breakdown: Dict  # Slab-wise breakdown
    is_rebate_eligible: bool  # Section 87A rebate for new regime
    rebate_amount: float


@dataclass
class TaxComparison:
    """Comparison of old vs new regime."""
    old_regime: TaxCalculationResult
    new_regime: TaxCalculationResult
    recommendation: str  # "old" or "new"
    tax_savings: float


# 2024-2025 FY Old Regime Slabs (Individuals)
OLD_REGIME_SLABS = [
    {"upper_limit": 300000, "rate": 0.00},
    {"upper_limit": 500000, "rate": 0.05},
    {"upper_limit": 750000, "rate": 0.10},
    {"upper_limit": 1000000, "rate": 0.15},
    {"upper_limit": 1250000, "rate": 0.20},
    {"upper_limit": 1500000, "rate": 0.25},
    {"upper_limit": float("inf"), "rate": 0.30},
]

# 2024-2025 FY New Regime Slabs (Individuals)
NEW_REGIME_SLABS = [
    {"upper_limit": 300000, "rate": 0.00},
    {"upper_limit": 600000, "rate": 0.05},
    {"upper_limit": 900000, "rate": 0.10},
    {"upper_limit": 1200000, "rate": 0.15},
    {"upper_limit": 1500000, "rate": 0.20},
    {"upper_limit": 1800000, "rate": 0.25},
    {"upper_limit": float("inf"), "rate": 0.30},
]

# Standard Deductions (2024-2025)
STANDARD_DEDUCTION = {
    "old": 40000,  # Old regime fixed deduction
    "new": 50000,  # New regime fixed deduction (2024 onwards)
}

# Deduction Categories with limits
DEDUCTION_LIMITS = {
    "80C": 150000,  # Life insurance, PPF, mutual funds, education, home loan principal
    "80D": 100000,  # Medical insurance premium (self + family, no dependent parents)
    "80D_parents": 50000,  # Additional for dependent parents aged 60+ (separate)
    "80CCD": 50000,  # Pension contribution to CCS
    "80E": float("inf"),  # Education loan interest
    "80EE": 200000,  # Home loan interest (first-time home buyers)
    "80EEA": 500000,  # Interest on loan for electric vehicles
}

# Cess
CESS_RATE = 0.04  # 4% health and education cess

# Section 87A Rebate (New Regime only) - for income <= 5L
REBATE_87A_LIMIT = 500000
REBATE_87A_RATE = 1.0  # Full rebate (100%) of tax for new regime if income <= 5L


def calculate_tax_for_slab(income: float, slabs: List[Dict]) -> Tuple[float, Dict]:
    """
    Calculate tax based on income slabs.
    Returns: (total_tax, breakdown_dict)
    """
    tax = 0.0
    previous_limit = 0
    breakdown = {}

    for slab in slabs:
        upper_limit = slab["upper_limit"]
        rate = slab["rate"]

        if income > previous_limit:
            taxable_in_slab = min(income, upper_limit) - previous_limit
            slab_tax = taxable_in_slab * rate
            tax += slab_tax

            slab_key = f"{previous_limit}-{upper_limit if upper_limit != float('inf') else '∞'}"
            breakdown[slab_key] = {
                "taxable_amount": taxable_in_slab,
                "rate": rate,
                "tax": slab_tax,
            }

        if income <= upper_limit:
            break

        previous_limit = upper_limit

    return tax, breakdown


def apply_deductions(gross_income: float, deductions: List[TaxDeduction]) -> Tuple[float, List[Dict]]:
    """
    Apply deductions to gross income.
    Returns: (taxable_income, applied_deductions_list)
    """
    applied = []
    total_deductions = 0.0

    for deduction in deductions:
        category = deduction.category
        amount = deduction.amount

        # Check limit for this category
        if category in DEDUCTION_LIMITS:
            limit = DEDUCTION_LIMITS[category]
            if amount > limit:
                applied_amount = limit
                warning = f"Limited to ₹{limit:,.0f}"
            else:
                applied_amount = amount
                warning = None
        else:
            applied_amount = amount
            warning = None

        total_deductions += applied_amount
        applied.append({
            "category": category,
            "description": deduction.description,
            "requested": amount,
            "applied": applied_amount,
            "warning": warning,
        })

    return max(0, gross_income - total_deductions), applied


def calculate_old_regime(
    gross_income: float, deductions: List[TaxDeduction]
) -> TaxCalculationResult:
    """Calculate tax under old regime (with standard deduction + other deductions)."""
    # Apply standard deduction first
    income_after_std = max(0, gross_income - STANDARD_DEDUCTION["old"])

    # Apply additional deductions
    taxable_income, applied_deductions = apply_deductions(income_after_std, deductions)

    # Calculate tax
    tax, breakdown = calculate_tax_for_slab(taxable_income, OLD_REGIME_SLABS)

    # Add 4% cess on tax amount
    cess = tax * CESS_RATE

    total_liability = tax + cess

    return TaxCalculationResult(
        regime="old",
        gross_income=gross_income,
        taxable_income=taxable_income,
        total_tax=tax,
        cess=cess,
        total_liability=total_liability,
        deductions_applied=applied_deductions,
        breakdown=breakdown,
        is_rebate_eligible=False,
        rebate_amount=0.0,
    )


def calculate_new_regime(
    gross_income: float, deductions: List[TaxDeduction]
) -> TaxCalculationResult:
    """
    Calculate tax under new regime.
    New regime: standard deduction only (no other deductions allowed).
    Section 87A rebate: full rebate if income <= 5L.
    """
    # Apply standard deduction (new regime doesn't allow other deductions)
    taxable_income = max(0, gross_income - STANDARD_DEDUCTION["new"])

    # Calculate tax
    tax, breakdown = calculate_tax_for_slab(taxable_income, NEW_REGIME_SLABS)

    # Check Section 87A rebate eligibility
    is_rebate_eligible = gross_income <= REBATE_87A_LIMIT
    rebate_amount = min(tax, tax * REBATE_87A_RATE) if is_rebate_eligible else 0.0

    # Tax after rebate
    tax_after_rebate = tax - rebate_amount

    # Add 4% cess
    cess = tax_after_rebate * CESS_RATE

    total_liability = tax_after_rebate + cess

    # In new regime, deductions are not applied to income (informational only)
    applied_deductions = [
        {
            "category": d.category,
            "description": d.description,
            "requested": d.amount,
            "applied": 0.0,
            "warning": "Deductions not allowed in new regime",
        }
        for d in deductions
    ]

    return TaxCalculationResult(
        regime="new",
        gross_income=gross_income,
        taxable_income=taxable_income,
        total_tax=tax,
        cess=cess,
        total_liability=total_liability,
        deductions_applied=applied_deductions,
        breakdown=breakdown,
        is_rebate_eligible=is_rebate_eligible,
        rebate_amount=rebate_amount,
    )


def compare_regimes(gross_income: float, deductions: List[TaxDeduction]) -> TaxComparison:
    """
    Compare old regime vs new regime.
    Returns recommendation (lower tax) and savings.
    """
    old = calculate_old_regime(gross_income, deductions)
    new = calculate_new_regime(gross_income, deductions)

    if new.total_liability < old.total_liability:
        recommendation = "new"
        tax_savings = old.total_liability - new.total_liability
    else:
        recommendation = "old"
        tax_savings = new.total_liability - old.total_liability

    return TaxComparison(
        old_regime=old,
        new_regime=new,
        recommendation=recommendation,
        tax_savings=tax_savings,
    )


def format_result_for_json(result: TaxCalculationResult) -> Dict:
    """Format result for JSON serialization."""
    return {
        "regime": result.regime,
        "gross_income": round(result.gross_income, 2),
        "taxable_income": round(result.taxable_income, 2),
        "total_tax": round(result.total_tax, 2),
        "cess": round(result.cess, 2),
        "total_liability": round(result.total_liability, 2),
        "deductions_applied": result.deductions_applied,
        "breakdown": result.breakdown,
        "is_rebate_eligible": result.is_rebate_eligible,
        "rebate_amount": round(result.rebate_amount, 2),
    }


def format_comparison_for_json(comparison: TaxComparison) -> Dict:
    """Format comparison for JSON serialization."""
    return {
        "old_regime": format_result_for_json(comparison.old_regime),
        "new_regime": format_result_for_json(comparison.new_regime),
        "recommendation": comparison.recommendation,
        "tax_savings": round(comparison.tax_savings, 2),
    }


# Test cases
if __name__ == "__main__":
    # Test 1: ₹5L income, no deductions
    print("Test 1: ₹5L income, no deductions")
    comparison = compare_regimes(500000, [])
    result = format_comparison_for_json(comparison)
    print(json.dumps(result, indent=2))
    print()

    # Test 2: ₹5L income with ₹2L 80C deduction
    print("Test 2: ₹5L income with ₹2L 80C deduction")
    deductions = [TaxDeduction("80C", "Life Insurance + PPF", 200000)]
    comparison = compare_regimes(500000, deductions)
    result = format_comparison_for_json(comparison)
    print(json.dumps(result, indent=2))
    print()

    # Test 3: ₹10L income with medical deduction
    print("Test 3: ₹10L income with medical deduction")
    deductions = [
        TaxDeduction("80C", "PPF + Life Insurance", 150000),
        TaxDeduction("80D", "Medical Insurance", 50000),
    ]
    comparison = compare_regimes(1000000, deductions)
    result = format_comparison_for_json(comparison)
    print(json.dumps(result, indent=2))
