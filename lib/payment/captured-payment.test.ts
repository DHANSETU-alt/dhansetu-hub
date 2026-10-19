import { describe, expect, it } from "vitest";
import { capturedPaymentId } from "./captured-payment";
const order = { id: "order_1", status: "paid", amount: 14900, currency: "INR", notes: {} };
const payment = { id: "pay_1", status: "captured", order_id: "order_1", amount: 14900, currency: "INR", amount_refunded: 0 };
describe("captured payment reconciliation", () => {
  it("finds the matching captured payment among failed attempts", () => {
    expect(capturedPaymentId(order, [{ ...payment, status: "failed" }, payment])).toBe("pay_1");
  });
  it("rejects a different order, wrong amount, currency, uncaptured or refunded payment", () => {
    for (const change of [{ order_id: "order_other" }, { amount: 1 }, { currency: "USD" }, { status: "authorized" }, { amount_refunded: 14900 }]) {
      expect(capturedPaymentId(order, [{ ...payment, ...change }])).toBeNull();
    }
  });
});
