import { describe, expect, it } from "vitest";
import { estimateSalariedTax } from "./india";

const input = (overrides: Partial<Parameters<typeof estimateSalariedTax>[0]> = {}) => ({ assessmentYear: "AY2026-27" as const, regime: "new" as const, resident: true, age: 30, grossSalaryPaise: 120000000, ...overrides });

describe("Indian salaried tax estimator", () => {
  it("returns nil tax after the AY2026-27 new-regime rebate for ₹12 lakh taxable income", () => {
    const result = estimateSalariedTax(input({ grossSalaryPaise: 127500000 }));
    expect(result.taxableIncomePaise).toBe(120000000);
    expect(result.taxBeforeTdsPaise).toBe(0);
    expect(result.status).toBe("nil");
  });
  it("compares a normal old-regime salary with TDS credit", () => {
    const result = estimateSalariedTax(input({ regime: "old", grossSalaryPaise: 100000000, oldRegimeDeductionsPaise: 15000000, tdsCreditPaise: 1000000 }));
    expect(result.taxableIncomePaise).toBe(80000000);
    expect(result.taxBeforeTdsPaise).toBeGreaterThan(0);
    expect(result.balancePaise).toBeLessThan(result.taxBeforeTdsPaise);
  });
  it("marks special-rate income as unsupported instead of guessing", () => {
    const result = estimateSalariedTax(input({ specialRateIncomePaise: 5000000 }));
    expect(result.unsupported).toContain("Special-rate income such as capital gains is not included.");
  });
});
