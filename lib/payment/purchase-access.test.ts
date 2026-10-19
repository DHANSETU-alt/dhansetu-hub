import { describe, expect, it } from "vitest";
import { purchaseCoversTier } from "./purchase-access";

describe("existing purchase coverage", () => {
  it("recognises both public plans and bundled Pro access", () => {
    expect(purchaseCoversTier("smartbudget_pro", "smartbudget_pro")).toBe(true);
    expect(purchaseCoversTier("all_access", "all_access")).toBe(true);
    expect(purchaseCoversTier("all_access", "smartbudget_pro")).toBe(true);
  });
  it("allows upgrades without granting unrelated plans", () => {
    expect(purchaseCoversTier("smartbudget_pro", "all_access")).toBe(false);
    expect(purchaseCoversTier("founding_lifetime", "all_access")).toBe(false);
  });
});
