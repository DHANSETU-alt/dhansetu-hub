export function razorpayLive() {
  const keyId = process.env.RAZORPAY_KEY_ID ?? "";
  const keyConfigured = Boolean(keyId && process.env.RAZORPAY_KEY_SECRET);
  const webhookSecretConfigured = Boolean(process.env.RAZORPAY_WEBHOOK_SECRET);
  const mode = keyId.startsWith("rzp_live_") ? "live" : keyId.startsWith("rzp_test_") ? "test" : "unknown";
  return {
    configured: keyConfigured && webhookSecretConfigured,
    keyConfigured,
    webhookSecretConfigured,
    mode,
    liveModeConfigured: keyConfigured && webhookSecretConfigured && mode === "live",
    // Presence of secrets is not evidence of a successful charge or webhook.
    transactionVerified: false,
  };
}
