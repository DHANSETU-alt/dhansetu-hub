import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd(), "..");

const ENV_RAZORPAY_KEY_SECRET = process.env.RAZORPAY_KEY_SECRET;

// Verifies a Checkout.js success callback server-side before trusting it.
// Checkout.js's handler runs entirely in the customer's browser -- a
// tampered client could claim success for an order that was never
// actually paid, so this signature check (Razorpay's own HMAC formula,
// see payment_gateway_manager.verify_razorpay_checkout_signature) is not
// optional. Real security boundary, not a formality.
export async function POST(req: NextRequest) {
  const body = await req.json();
  const { orderId, paymentId, signature } = body;

  if (!orderId || !paymentId || !signature) {
    return NextResponse.json({ error: "orderId, paymentId, and signature are required" }, { status: 400 });
  }

  const keySecret = ENV_RAZORPAY_KEY_SECRET;
  if (!keySecret) {
    return NextResponse.json({ error: "Payment service is not configured" }, { status: 503 });
  }

  const args = [
    "-m", "orchestrator.cli", "--verify-razorpay-payment",
    "--razorpay-key-secret", keySecret,
    "--order-id", orderId, "--payment-id", paymentId, "--razorpay-signature", signature,
  ];

  try {
    const { stdout } = await execFileAsync("python3", args, {
      cwd: PROJECT_ROOT, timeout: 20_000,
    });
    const lastLine = stdout.trim().split("\n").pop() || "{}";
    const result = JSON.parse(lastLine);
    if (result.error || result.verified === false) {
      return NextResponse.json(result, { status: result.error ? 422 : 400 });
    }
    return NextResponse.json({ ...result, verified: true });
  } catch (e) {
    const err = e as { stderr?: string; message?: string };
    return NextResponse.json({ error: (err.stderr || err.message || "Verification failed").trim(), verified: false }, { status: 422 });
  }
}
