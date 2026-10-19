import { beforeEach, describe, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ fetch: vi.fn(), purchase: vi.fn() }));
vi.mock("./razorpay", () => ({ fetchOrder: mocks.fetch }));
vi.mock("./records", () => ({ purchaseByOrder: mocks.purchase }));
import { validatedPaidOrder } from "./validate-order";
beforeEach(() => {
  mocks.fetch.mockResolvedValue({ id: "order_1", amount: 14900, currency: "INR", status: "paid", notes: { tier: "smartbudget_pro", user_id: "user-1" } });
  mocks.purchase.mockResolvedValue({ tier: "smartbudget_pro", user_id: "user-1", amount_paise: 14900, currency: "INR" });
});
describe("provider payment confirmation", () => {
  it("accepts a paid order with matching account, tier, amount and currency", async () => {
    await expect(validatedPaidOrder("order_1")).resolves.toHaveProperty("purchase.user_id", "user-1");
  });
  it("rejects an authorised but uncaptured order", async () => {
    mocks.fetch.mockResolvedValue({ status: "attempted" });
    await expect(validatedPaidOrder("order_1")).rejects.toThrow("capture is still pending");
  });
  it("rejects mismatched provider amounts", async () => {
    mocks.fetch.mockResolvedValue({ status: "paid", amount: 1, currency: "INR", notes: { tier: "smartbudget_pro", user_id: "user-1" } });
    await expect(validatedPaidOrder("order_1")).rejects.toThrow("amount mismatch");
  });
});
