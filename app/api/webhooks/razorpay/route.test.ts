import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { signPayload } from "@/lib/payment/signatures";

const mocks = vi.hoisted(() => ({ validate: vi.fn(), grant: vi.fn(), revoke: vi.fn() }));
vi.mock("@/lib/payment/validate-order", () => ({ validatedPaidOrder: mocks.validate }));
vi.mock("@/lib/payment/entitlement", () => ({ grantEntitlement: mocks.grant, revokeEntitlement: mocks.revoke }));
import { POST } from "@/app/api/webhooks/razorpay/route";

const secret = "webhook-test-secret";
function request(payload: unknown, signature = true) {
  const body = JSON.stringify(payload);
  return new NextRequest("https://dhansetuhub.in/api/webhooks/razorpay", {
    method: "POST", body, headers: { "x-razorpay-signature": signature ? signPayload(body, secret) : "bad" },
  });
}
beforeEach(() => {
  process.env.RAZORPAY_WEBHOOK_SECRET = secret;
  vi.resetAllMocks();
  mocks.validate.mockResolvedValue({ purchase: { user_id: "user-1", tier: "smartbudget_pro" } });
  mocks.grant.mockResolvedValue({ granted: true, idempotent: false });
  mocks.revoke.mockResolvedValue({ revoked: true, idempotent: false, partial: false });
});
describe("Razorpay webhook", () => {
  it("rejects forged signatures before processing payment state", async () => {
    expect((await POST(request({ event: "payment.captured" }, false))).status).toBe(401);
    expect(mocks.grant).not.toHaveBeenCalled(); expect(mocks.revoke).not.toHaveBeenCalled();
  });
  it("grants only a signed captured payment after provider validation", async () => {
    const response = await POST(request({ event: "payment.captured", payload: { payment: { entity: { id: "pay_1", order_id: "order_1" } } } }));
    expect(response.status).toBe(200);
    expect(mocks.grant).toHaveBeenCalledWith("order_1", "pay_1", "user-1", "smartbudget_pro");
  });
  it("reconciles a signed full refund without issuing a refund", async () => {
    const response = await POST(request({ event: "refund.processed", payload: { refund: { entity: { id: "rfnd_1", payment_id: "pay_1", amount: 14900 } } } }));
    expect(response.status).toBe(200);
    expect(mocks.revoke).toHaveBeenCalledWith("pay_1", "rfnd_1", 14900);
    expect(mocks.grant).not.toHaveBeenCalled();
  });
  it("rejects incomplete signed refund payloads", async () => {
    expect((await POST(request({ event: "refund.processed", payload: { refund: { entity: { id: "rfnd_1", amount: 0 } } } }))).status).toBe(422);
    expect(mocks.revoke).not.toHaveBeenCalled();
  });
});
