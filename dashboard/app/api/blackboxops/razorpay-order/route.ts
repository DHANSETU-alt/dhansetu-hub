import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd(), "..");

// Same "server env always wins over a browser-supplied key" rule as
// subscribe/route.ts -- this is real money movement, the client-supplied
// fields exist only for the pricing page's own "Founder Test Mode" panel.
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
  const { amountInr, receipt, razorpayKeyId, razorpaySecret, product } = body;

  if (!amountInr || !receipt) {
    return NextResponse.json({ error: "amountInr and receipt are required" }, { status: 400 });
  }

  const keyId = ENV_RAZORPAY_KEY_ID || razorpayKeyId;
  const keySecret = ENV_RAZORPAY_KEY_SECRET || razorpaySecret;
  const credentialSource = ENV_RAZORPAY_KEY_ID && ENV_RAZORPAY_KEY_SECRET ? "server_env" : "browser_test_mode";
  if (!keyId || !keySecret) {
    return NextResponse.json({ error: "Razorpay key ID and secret are required" }, { status: 400 });
  }

  const args = [
    "-m", "orchestrator.cli", "--create-razorpay-order",
    "--razorpay-key-id", keyId, "--razorpay-key-secret", keySecret,
    "--amount-inr", String(amountInr), "--receipt", receipt,
  ];
  if (product) args.push("--product", product);

  try {
    const { stdout } = await execFileAsync("python3", args, { cwd: PROJECT_ROOT, timeout: 20_000 });
    const lastLine = stdout.trim().split("\n").pop() || "{}";
    const result = JSON.parse(lastLine);
    if (result.error) {
      return NextResponse.json({ ...result, credentialSource }, { status: 422 });
    }
    // key_id is safe to hand back to the browser -- Checkout.js needs it
    // to open the modal, and a Razorpay Key ID (unlike the Key Secret) is
    // meant to be public, the same way a Stripe publishable key is.
    return NextResponse.json({ ...result, keyId, credentialSource });
  } catch (e) {
    const err = e as { stderr?: string; message?: string };
    return NextResponse.json({ error: (err.stderr || err.message || "Order creation failed").trim() }, { status: 422 });
  }
}
