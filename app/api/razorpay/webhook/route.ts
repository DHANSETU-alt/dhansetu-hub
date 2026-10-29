// Compatibility alias for the webhook URL already configured in the Razorpay dashboard.
// Keep the canonical implementation in /api/webhooks/razorpay so every delivery path
// shares the same raw-body signature check and idempotent entitlement grant.
export { POST } from "@/app/api/webhooks/razorpay/route";
