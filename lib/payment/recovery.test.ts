import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
const mocks = vi.hoisted(() => ({ user: vi.fn(), purchase: vi.fn(), validate: vi.fn(), captured: vi.fn(), grant: vi.fn(), active: vi.fn() }));
vi.mock("@/lib/payment/auth", () => ({ authenticatedUser: mocks.user }));
vi.mock("@/lib/payment/records", () => ({ purchaseByOrder: mocks.purchase }));
vi.mock("@/lib/payment/validate-order", () => ({ validatedPaidOrder: mocks.validate }));
vi.mock("@/lib/payment/razorpay", () => ({ fetchCapturedPaymentId: mocks.captured }));
vi.mock("@/lib/payment/entitlement", () => ({ grantEntitlement: mocks.grant, hasEntitlement: mocks.active }));
import { GET } from "@/app/api/entitlement/route";
const request = () => new NextRequest("https://dhansetuhub.in/api/entitlement?order=order_1");
beforeEach(() => {
  vi.resetAllMocks();
  mocks.user.mockResolvedValue({ id: "user-1", email: "buyer@example.test" });
  mocks.purchase.mockResolvedValue({ user_id: "user-1", status: "created", tier: "smartbudget_pro" });
  mocks.validate.mockResolvedValue({ order: { id: "order_1" } });
  mocks.captured.mockResolvedValue("pay_1"); mocks.grant.mockResolvedValue({ granted: true }); mocks.active.mockResolvedValue(true);
});
describe("automatic payment recovery", () => {
  it("reconciles a captured payment when both delivery paths were lost", async () => {
    expect(await (await GET(request())).json()).toMatchObject({ active: true });
    expect(mocks.grant).toHaveBeenCalledWith("order_1", "pay_1", "user-1", "smartbudget_pro", "buyer@example.test");
  });
  it("rejects another account before provider access or granting", async () => {
    mocks.purchase.mockResolvedValue({ user_id: "someone-else" });
    expect((await GET(request())).status).toBe(404); expect(mocks.validate).not.toHaveBeenCalled(); expect(mocks.grant).not.toHaveBeenCalled();
  });
  it("keeps pending orders recoverable without granting access", async () => {
    mocks.validate.mockRejectedValue(new Error("Capture pending"));
    const response = await GET(request());
    expect(response.status).toBe(202); expect(await response.json()).toMatchObject({ active: false, pending: true }); expect(mocks.grant).not.toHaveBeenCalled();
  });
  it("does not replay provider calls for a recorded paid purchase", async () => {
    mocks.purchase.mockResolvedValue({ user_id: "user-1", status: "paid" });
    expect(await (await GET(request())).json()).toMatchObject({ active: true }); expect(mocks.validate).not.toHaveBeenCalled();
  });
});
