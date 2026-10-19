import { verifySignature } from "@/lib/payment/signatures";

export function razorpayLiveCheck() {
  return {
    keyConfigured: Boolean(process.env.RAZORPAY_KEY_ID && process.env.RAZORPAY_KEY_SECRET),
    webhookSecretConfigured: Boolean(process.env.RAZORPAY_WEBHOOK_SECRET),
    signatureVerifier: typeof verifySignature === "function",
  };
}
