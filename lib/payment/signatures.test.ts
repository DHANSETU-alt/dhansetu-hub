import { describe, expect, it } from "vitest";
import { signPayload, verifySignature } from "./signatures";

describe("Razorpay signatures", () => {
  it("accepts the exact HMAC", () => { const signature = signPayload("order|payment", "secret"); expect(verifySignature("order|payment", signature, "secret")).toBe(true); });
  it("rejects tampering and malformed input", () => { const signature = signPayload("order|payment", "secret"); expect(verifySignature("order|tampered", signature, "secret")).toBe(false); expect(verifySignature("x", "bad", "secret")).toBe(false); });
});
