import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";
import { randomUUID } from "crypto";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd(), "..");

const ENV_RAZORPAY_KEY_ID = process.env.RAZORPAY_KEY_ID;
const ENV_RAZORPAY_KEY_SECRET = process.env.RAZORPAY_KEY_SECRET;

// Creates a real Razorpay Order for a FIXED amount -- this is the
// Orders + Checkout.js pattern, not a Payment Link. The frontend takes
// this order_id straight into Razorpay's own Checkout modal; no separate
// link is ever generated, copied, or shared. See orchestrator/
// payment_gateway_manager.py's create_razorpay_order() for the actual
// Razorpay API call and the comment explaining why this exists as a
// distinct path from the Payment Links flow above it in that file.
export async function POST(req: NextRequest) {
  const body = await req.json();
  const { product, customerName, customerEmail, customerContact } = body;

  if (typeof product !== "string" || !product) {
    return NextResponse.json({ error: "product is required" }, { status: 400 });
  }

  if (customerEmail && typeof customerEmail !== "string") {
    return NextResponse.json({ error: "customerEmail must be a string" }, { status: 400 });
  }

  const keyId = ENV_RAZORPAY_KEY_ID;
  const keySecret = ENV_RAZORPAY_KEY_SECRET;
  if (!keyId || !keySecret) {
    return NextResponse.json({ error: "Payment service is not configured" }, { status: 503 });
  }

  const args = [
    "-m", "orchestrator.cli", "--create-razorpay-order",
    "--receipt", `${product}_${randomUUID()}`, "--product", product,
  ];

  if (customerName) args.push("--customer-name", customerName);
  if (customerEmail) args.push("--customer-email", customerEmail);
  if (customerContact) args.push("--customer-contact", customerContact);

  try {
    const { stdout } = await execFileAsync("python3", args, {
      cwd: PROJECT_ROOT, timeout: 20_000,
      env: { ...process.env, RAZORPAY_KEY_ID: keyId, RAZORPAY_KEY_SECRET: keySecret },
    });
    const lastLine = stdout.trim().split("\n").pop() || "{}";
    const result = JSON.parse(lastLine);
    if (result.error) {
      return NextResponse.json(result, { status: 422 });
    }
    // key_id is safe to hand back to the browser -- Checkout.js needs it
    // to open the modal, and a Razorpay Key ID (unlike the Key Secret) is
    // meant to be public, the same way a Stripe publishable key is.
    return NextResponse.json({ ...result, keyId });
  } catch (e) {
    const err = e as { stderr?: string; message?: string };
    return NextResponse.json({ error: (err.stderr || err.message || "Order creation failed").trim() }, { status: 422 });
  }
}
