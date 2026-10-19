import { afterEach, describe, expect, it, vi } from "vitest";
import { razorpayLive } from "./razorpay-live";

afterEach(() => vi.unstubAllEnvs());
function configure(key: string, secret = "test-secret", webhook = "test-webhook") {
  vi.stubEnv("RAZORPAY_KEY_ID", key);
  vi.stubEnv("RAZORPAY_KEY_SECRET", secret);
  vi.stubEnv("RAZORPAY_WEBHOOK_SECRET", webhook);
}
describe("payment configuration status", () => {
  it("does not report test credentials as live", () => {
    configure("rzp_test_example");
    expect(razorpayLive()).toMatchObject({ configured: true, mode: "test", liveModeConfigured: false, transactionVerified: false });
  });
  it("separates live configuration from verified transactions", () => {
    configure("rzp_live_example");
    expect(razorpayLive()).toMatchObject({ liveModeConfigured: true, transactionVerified: false });
  });
  it("requires both server and webhook secrets", () => {
    configure("rzp_live_example", "", "");
    expect(razorpayLive().configured).toBe(false);
  });
});
