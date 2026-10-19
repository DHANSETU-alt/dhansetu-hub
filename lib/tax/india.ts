export type TaxRegime = "old" | "new";

export type SalariedTaxInput = {
  assessmentYear: "AY2025-26" | "AY2026-27";
  regime: TaxRegime;
  resident: boolean;
  age: number;
  grossSalaryPaise: number;
  otherNormalIncomePaise?: number;
  tdsCreditPaise?: number;
  oldRegimeDeductionsPaise?: number;
  specialRateIncomePaise?: number;
};

export type TaxEstimate = {
  assessmentYear: SalariedTaxInput["assessmentYear"];
  regime: TaxRegime;
  taxableIncomePaise: number;
  standardDeductionPaise: number;
  deductionsPaise: number;
  slabTaxPaise: number;
  rebatePaise: number;
  cessPaise: number;
  taxBeforeTdsPaise: number;
  tdsCreditPaise: number;
  balancePaise: number;
  status: "payable" | "refund" | "nil";
  ruleVersion: string;
  assumptions: string[];
  unsupported: string[];
};

const paise = (rupees: number) => Math.round(rupees * 100);
const floor0 = (value: number) => Math.max(0, Math.round(value));

// Official references retained with the rule version for auditability:
// https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-3
// https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1
const RULE_VERSION = "2026-09-22 / AY2025-26 + AY2026-27 official salaried slabs";

function slabTax(rupees: number, regime: TaxRegime, assessmentYear: SalariedTaxInput["assessmentYear"]): number {
  if (assessmentYear === "AY2025-26") {
    if (regime === "old") return rupees <= 250000 ? 0 : rupees <= 500000 ? (rupees - 250000) * .05 : rupees <= 1000000 ? 12500 + (rupees - 500000) * .2 : 112500 + (rupees - 1000000) * .3;
    return rupees <= 300000 ? 0 : rupees <= 700000 ? (rupees - 300000) * .05 : rupees <= 1000000 ? 20000 + (rupees - 700000) * .1 : rupees <= 1200000 ? 50000 + (rupees - 1000000) * .15 : rupees <= 1500000 ? 80000 + (rupees - 1200000) * .2 : 140000 + (rupees - 1500000) * .3;
  }
  if (regime === "old") return rupees <= 250000 ? 0 : rupees <= 500000 ? (rupees - 250000) * .05 : rupees <= 1000000 ? 12500 + (rupees - 500000) * .2 : 112500 + (rupees - 1000000) * .3;
  return rupees <= 400000 ? 0 : rupees <= 800000 ? (rupees - 400000) * .05 : rupees <= 1200000 ? 20000 + (rupees - 800000) * .1 : rupees <= 1600000 ? 60000 + (rupees - 1200000) * .15 : rupees <= 2000000 ? 120000 + (rupees - 1600000) * .2 : rupees <= 2400000 ? 200000 + (rupees - 2000000) * .25 : 300000 + (rupees - 2400000) * .3;
}

export function estimateSalariedTax(input: SalariedTaxInput): TaxEstimate {
  const unsupported: string[] = [];
  if (input.specialRateIncomePaise && input.specialRateIncomePaise > 0) unsupported.push("Special-rate income such as capital gains is not included.");
  if (!input.resident) unsupported.push("Non-resident rules require separate income classification and are not included.");
  if (input.age >= 60) unsupported.push("Senior-citizen thresholds are not yet enabled in this first salaried version.");
  if (input.grossSalaryPaise < 0 || (input.otherNormalIncomePaise ?? 0) < 0) throw new Error("Income values cannot be negative");
  const standardDeductionPaise = input.regime === "new" ? paise(input.assessmentYear === "AY2026-27" ? 75000 : 75000) : paise(50000);
  const deductionsPaise = input.regime === "old" ? Math.min(floor0(input.oldRegimeDeductionsPaise ?? 0), paise(150000)) : 0;
  const taxableIncomePaise = floor0(input.grossSalaryPaise + (input.otherNormalIncomePaise ?? 0) - standardDeductionPaise - deductionsPaise);
  const slabTaxPaise = paise(slabTax(taxableIncomePaise / 100, input.regime, input.assessmentYear));
  const rebateLimit = input.assessmentYear === "AY2026-27" && input.regime === "new" ? paise(1200000) : input.regime === "new" ? paise(700000) : paise(500000);
  const rebateCap = input.assessmentYear === "AY2026-27" && input.regime === "new" ? paise(60000) : input.regime === "new" ? paise(25000) : paise(12500);
  const rebatePaise = input.resident && taxableIncomePaise <= rebateLimit ? Math.min(slabTaxPaise, rebateCap) : 0;
  const cessPaise = paise((slabTaxPaise - rebatePaise) / 100 * .04);
  const taxBeforeTdsPaise = floor0(slabTaxPaise - rebatePaise + cessPaise);
  const tdsCreditPaise = floor0(input.tdsCreditPaise ?? 0);
  const balancePaise = taxBeforeTdsPaise - tdsCreditPaise;
  return { assessmentYear: input.assessmentYear, regime: input.regime, taxableIncomePaise, standardDeductionPaise, deductionsPaise, slabTaxPaise, rebatePaise, cessPaise, taxBeforeTdsPaise, tdsCreditPaise, balancePaise, status: balancePaise > 0 ? "payable" : balancePaise < 0 ? "refund" : "nil", ruleVersion: RULE_VERSION, assumptions: ["Normal-rate salary and other income only", "Cess is 4% after rebate", "Old-regime deductions are capped at ₹1,50,000 in this first version", "This is an estimate, not a tax filing or professional advice"], unsupported };
}
