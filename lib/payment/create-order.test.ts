import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const mocks = vi.hoisted(() => ({ user: vi.fn(), purchases: vi.fn(), rate: vi.fn(), seats: vi.fn(), save: vi.fn(), create: vi.fn(), fetch: vi.fn(), key: vi.fn() }));
vi.mock("@/lib/payment/auth", () => ({ authenticatedUser: mocks.user }));
vi.mock("@/lib/payment/records", () => ({ purchasesForUser: mocks.purchases, checkoutRateAllowed: mocks.rate, seatsRemaining: mocks.seats, saveCreatedPurchase: mocks.save }));
vi.mock("@/lib/payment/razorpay", () => ({ createOrder: mocks.create, fetchOrder: mocks.fetch, razorpayKeyId: mocks.key }));
import { POST } from "@/app/api/checkout/create-order/route";

function request(body: unknown = { tier: "smartbudget_pro", consent: true }) {
  return new NextRequest("https://dhansetuhub.in/api/checkout/create-order", { method: "POST", body: JSON.stringify(body), headers: { "content-type": "application/json" } });
}
beforeEach(() => {
  vi.resetAllMocks();
  mocks.user.mockResolvedValue({ id: "user-1", email: "customer@example.test" });
  mocks.purchases.mockResolvedValue([]); mocks.rate.mockResolvedValue(true); mocks.seats.mockResolvedValue(10);
  mocks.create.mockResolvedValue({ id: "order_new" }); mocks.key.mockReturnValue("rzp_test_example");
});
describe("checkout order route", () => {
  it("rejects unsigned callers without touching purchase history", async () => {
    mocks.user.mockResolvedValue(null);
    expect((await POST(request())).status).toBe(401);
    expect(mocks.purchases).not.toHaveBeenCalled(); expect(mocks.create).not.toHaveBeenCalled();
  });
  it("restores a paid bundle instead of charging for included Pro", async () => {
    mocks.purchases.mockResolvedValue([{ status: "paid", tier: "all_access", razorpay_order_id: "order_paid" }]);
    const response = await POST(request());
    expect(await response.json()).toEqual({ existingAccess: true, orderId: "order_paid" });
    expect(mocks.create).not.toHaveBeenCalled(); expect(mocks.save).not.toHaveBeenCalled();
  });
  it("allows Pro to upgrade and takes the amount only from the server", async () => {
    mocks.purchases.mockResolvedValue([{ status: "paid", tier: "smartbudget_pro", razorpay_order_id: "order_pro" }]);
    const response = await POST(request({ tier: "all_access", consent: true, amount: 1 }));
    expect((await response.json()).amount).toBe(39900);
    expect(mocks.create).toHaveBeenCalledWith(expect.objectContaining({ amount: 39900, tier: "all_access" }));
  });
  it("reuses an unresolved order without creating another charge", async () => {
    mocks.purchases.mockResolvedValue([{ status: "created", tier: "smartbudget_pro", razorpay_order_id: "order_pending" }]);
    mocks.fetch.mockResolvedValue({ id: "order_pending", status: "created", amount: 14900, currency: "INR", notes: { user_id: "user-1", tier: "smartbudget_pro" } });
    const response = await POST(request());
    expect(await response.json()).toMatchObject({ orderId: "order_pending", amount: 14900 }); expect(mocks.create).not.toHaveBeenCalled();
  });
  it("recovers captured payments awaiting the webhook without opening checkout", async () => {
    mocks.purchases.mockResolvedValue([{ status: "created", tier: "smartbudget_pro", razorpay_order_id: "order_pending" }]);
    mocks.fetch.mockResolvedValue({ id: "order_pending", status: "paid", amount: 14900, currency: "INR", notes: { user_id: "user-1", tier: "smartbudget_pro" } });
    expect(await (await POST(request())).json()).toEqual({ recovery: true, orderId: "order_pending" });
    expect(mocks.create).not.toHaveBeenCalled();
  });
  it("returns a recoverable error without provider internals", async () => {
    mocks.rate.mockRejectedValue(new Error("private database details"));
    const response = await POST(request());
    expect(response.status).toBe(503); expect(JSON.stringify(await response.json())).not.toContain("private database");
  });
});
