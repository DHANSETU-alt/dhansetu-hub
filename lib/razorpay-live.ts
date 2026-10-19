export function razorpayLive() {
  return {
    live: Boolean(process.env.RAZORPAY_KEY_ID && process.env.RAZORPAY_KEY_SECRET && process.env.RAZORPAY_WEBHOOK_SECRET),
    webhookSignature: true,
  };
}
