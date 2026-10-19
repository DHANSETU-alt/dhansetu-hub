import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd(), "..");

const RAZORPAY_WEBHOOK_SECRET = process.env.RAZORPAY_WEBHOOK_SECRET;

// Real gap flagged in orchestrator/payments.py's own docstring and left
// open until now: "No webhook receiver -- this system is localhost-only
// by design... payment status is checked on demand." This is the
// authoritative, server-to-server confirmation Razorpay sends when a
// payment actually completes -- distinct from razorpay-verify/route.ts,
// which only covers the customer's own browser reporting success (real,
// but a browser can crash/go offline after payment but before that call
// lands). Configure this URL as the webhook endpoint in the Razorpay
// dashboard once real credentials exist, with a real Webhook Secret
// (separate from the API Key Secret) set as RAZORPAY_WEBHOOK_SECRET.
export async function POST(req: NextRequest) {
  // req.text() -- NOT req.json() -- is required here: the signature
  // covers the exact raw bytes Razorpay sent. Re-serializing a parsed
  // object (even one that round-trips to "the same" JSON) can produce
  // different byte content (key order, whitespace) and silently break
  // verification. See orchestrator/payment_gateway_manager.py's
  // verify_razorpay_webhook_signature docstring for the same warning.
  const rawBody = await req.text();
  const signature = req.headers.get("x-razorpay-signature");
  const webhookId = req.headers.get("x-razorpay-event-id"); // For idempotency tracking

  if (!signature) {
    return NextResponse.json({ error: "missing x-razorpay-signature header" }, { status: 400 });
  }
  if (!RAZORPAY_WEBHOOK_SECRET) {
    // Fail loud, not silent -- an unconfigured webhook secret must never
    // be treated as "nothing to verify, accept anyway."
    return NextResponse.json({ error: "RAZORPAY_WEBHOOK_SECRET is not configured on this server" }, { status: 500 });
  }

  const args = [
    "-m", "orchestrator.cli", "--process-razorpay-webhook",
    "--webhook-secret", RAZORPAY_WEBHOOK_SECRET,
    "--raw-body", rawBody,
    "--razorpay-signature", signature,
  ];

  if (webhookId) args.push("--webhook-id", webhookId);

  try {
    const { stdout } = await execFileAsync("python3", args, { cwd: PROJECT_ROOT, timeout: 20_000 });
    const lastLine = stdout.trim().split("\n").pop() || "{}";
    const result = JSON.parse(lastLine);
    if (result.error) {
      // Razorpay retries on non-2xx, which is correct for a real
      // processing failure -- but a signature failure should NOT be
      // retried (retrying won't make a forged signature valid), so that
      // specific case still returns 200 to stop the retry storm, with
      // the failure visible in the response body for our own logs.
      const status = result.verified === false ? 200 : 422;
      return NextResponse.json(result, { status });
    }
    return NextResponse.json({ ...result, processed: true });
  } catch (e) {
    const err = e as { stderr?: string; message?: string };
    return NextResponse.json({ error: (err.stderr || err.message || "Webhook processing failed").trim() }, { status: 422 });
  }
}
