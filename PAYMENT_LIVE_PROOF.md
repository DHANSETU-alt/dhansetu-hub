# Payment live proof

Origin health is currently HTTP 200. Payment readiness is exposed at `/api/payment/verify-live`.
The endpoint returns HTTP 200 only when Razorpay key ID, key secret, webhook secret, and signature verification are configured.

Current evidence: Razorpay environment variables are not present in this session, so payment readiness is not claimed as live.
