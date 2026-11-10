import { beforeEach, describe, expect, it } from "vitest";
import { createTestOrder, getTestOrder, grantTestEntitlement, resetTestStore, revokeTestEntitlement, testSnapshot } from "./test-store";

beforeEach(() => resetTestStore());
async function paid(tier: "smartbudget_pro" | "all_access" = "smartbudget_pro") {
  const order = createTestOrder("user-1", tier, { consented_at: "2026-10-23T00:00:00Z", consent_ip: "127.0.0.1", terms_version: "test" });
  await grantTestEntitlement(order.id, `pay_${tier}`, "user-1", tier);
  return order;
}
describe("refund reconciliation", () => {
  it("keeps access after a partial refund and records the state", async () => {
    await paid();
    await expect(revokeTestEntitlement("pay_smartbudget_pro", "rfnd_partial", 100)).resolves.toEqual({ revoked: false, idempotent: false, partial: true });
    expect(testSnapshot().purchases[0]).toMatchObject({ status: "partially_refunded", refunded_amount_paise: 100 });
    expect(testSnapshot().plans).toEqual({ "user-1": "smartbudget_pro" });
  });
  it("revokes a fully refunded entitlement exactly once", async () => {
    const order = await paid();
    await expect(revokeTestEntitlement("pay_smartbudget_pro", "rfnd_full", 14900)).resolves.toEqual({ revoked: true, idempotent: false, partial: false });
    await expect(revokeTestEntitlement("pay_smartbudget_pro", "rfnd_full", 14900)).resolves.toEqual({ revoked: false, idempotent: true, partial: false });
    expect(testSnapshot().purchases[0]).toMatchObject({ status: "refunded", refunded_amount_paise: 14900 });
    expect(testSnapshot().plans).toEqual({});
    expect(getTestOrder(testSnapshot().purchases[0].razorpay_order_id)?.status).toBe("refunded");
    await expect(grantTestEntitlement(order.id, "pay_smartbudget_pro", "user-1", "smartbudget_pro")).rejects.toThrow("not eligible for activation");
  });
  it("preserves an All Access entitlement when Pro is refunded", async () => {
    await paid("smartbudget_pro"); await paid("all_access");
    await revokeTestEntitlement("pay_smartbudget_pro", "rfnd_pro", 14900);
    expect(testSnapshot().plans).toEqual({ "user-1": "all_access" });
  });
  it("rejects a refund total above the original payment", async () => {
    await paid();
    await expect(revokeTestEntitlement("pay_smartbudget_pro", "rfnd_bad", 14901)).rejects.toThrow("exceeds payment amount");
  });
});
