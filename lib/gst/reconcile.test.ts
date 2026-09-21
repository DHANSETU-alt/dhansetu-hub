import { describe, expect, it } from "vitest";
import { reconcileGst, type GstInvoice } from "./reconcile";

const row = (invoiceNumber: string, taxPaise: number): GstInvoice => ({ invoiceNumber, supplierGstin: "27ABCDE1234F1Z5", taxableValuePaise: taxPaise * 10, taxPaise });
describe("GST reconciliation", () => {
  it("matches identical invoices", () => { const result = reconcileGst([row("A1", 1800)], [row("A1", 1800)]); expect(result.matched).toBe(1); expect(result.review).toHaveLength(0); });
  it("flags missing and mismatched records without promising recovery", () => { const result = reconcileGst([row("A1", 1800), row("A2", 900)], [row("A1", 1900)]); expect(result.review.map((item) => item.reason)).toEqual(["value_mismatch", "missing_in_2b"]); expect(result.note).toContain("does not guarantee"); });
  it("flags duplicate invoice keys", () => { const result = reconcileGst([row("A1", 1800), row("A1", 1800)], [row("A1", 1800)]); expect(result.review[0].reason).toBe("duplicate"); });
});
