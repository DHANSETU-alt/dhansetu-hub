import { describe, expect, it } from "vitest";
import { analyzeExpense, auditInvoice, parseForm16, reminderTone, suggestHsn } from "./local-adapters";

describe("AI Studio local adapters", () => {
  it("generates bounded reminder text without external calls", () => {
    expect(reminderTone({ clientName: "Demo Co", invoiceNo: "INV-1", amount: "1000", dueDate: "2026-11-01", tone: "Professional" })).toContain("INV-1");
  });

  it("classifies common service descriptions", () => {
    expect(suggestHsn("UI design consulting").hsn).toBe("998311");
    expect(suggestHsn("SEO marketing").hsn).toBe("998361");
  });

  it("returns an invoice pre-check and expense ITC decision", () => {
    expect(auditInvoice({ invNo: "INV-1", seller: { gstin: "24AAA", stateCode: "24" }, buyer: { gstin: "27BBB", stateCode: "27" } }).riskScore).toBe("LOW");
    expect(analyzeExpense({ category: "Fuel", amount: 100, gstRate: 18 }).itcStatus).toBe("BLOCKED_17_5");
  });

  it("extracts the synthetic Form 16 demo fields", () => {
    expect(parseForm16("Gross Salary: ₹15,20,000, 80C: ₹1,50,000, TDS: ₹1,10,000")).toMatchObject({ grossSalary: 1520000, sec80C: 150000, tdsDeducted: 110000 });
  });
});
