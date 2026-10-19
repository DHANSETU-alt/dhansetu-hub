import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd(), "..");

// Server-side credentials, when set, always win over whatever the browser
// sent -- a client-supplied key is a staging convenience (the "Founder Test
// Mode" panel), never something a real checkout route should trust once a
// real merchant account exists. Set these in the hosting environment
// (.env.local here, real env vars in production) and the browser panel
// becomes dead code automatically -- no separate flag needed.
const ENV_RAZORPAY_KEY_ID = process.env.RAZORPAY_KEY_ID;
const ENV_RAZORPAY_KEY_SECRET = process.env.RAZORPAY_KEY_SECRET;
const ENV_PAYU_MERCHANT_KEY = process.env.PAYU_MERCHANT_KEY;
const ENV_PAYU_MERCHANT_SALT = process.env.PAYU_MERCHANT_SALT;

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { email, product, gateway } = body;

  if (!email || !product || !gateway) {
    return NextResponse.json({ error: "email, product, and gateway are required" }, { status: 400 });
  }

  const args = ["-m", "orchestrator.cli", "--subscribe", "--email", email, "--product", product, "--gateway", gateway];
  if (gateway === "razorpay") {
    const keyId = ENV_RAZORPAY_KEY_ID;
    const keySecret = ENV_RAZORPAY_KEY_SECRET;
    if (!keyId || !keySecret) {
      return NextResponse.json({ error: "Razorpay key ID and secret are required for this gateway" }, { status: 400 });
    }
    // Credentials are supplied through the child environment below so
    // they never appear in process listings.
  } else if (gateway === "payu") {
    const merchantKey = ENV_PAYU_MERCHANT_KEY;
    const merchantSalt = ENV_PAYU_MERCHANT_SALT;
    if (!merchantKey || !merchantSalt) {
      return NextResponse.json({ error: "PayU merchant key and salt are required for this gateway" }, { status: 400 });
    }
    const origin = req.nextUrl.origin;
    args.push("--success-url", `${origin}/blackboxops-os/pricing?paid=1`, "--failure-url", `${origin}/blackboxops-os/pricing?failed=1`);
  } else {
    return NextResponse.json({ error: "gateway must be 'razorpay' or 'payu'" }, { status: 400 });
  }

  try {
    const { stdout } = await execFileAsync("python3", args, {
      cwd: PROJECT_ROOT, timeout: 20_000,
      env: {
        ...process.env,
        RAZORPAY_KEY_ID: ENV_RAZORPAY_KEY_ID,
        RAZORPAY_KEY_SECRET: ENV_RAZORPAY_KEY_SECRET,
        PAYU_MERCHANT_KEY: ENV_PAYU_MERCHANT_KEY,
        PAYU_MERCHANT_SALT: ENV_PAYU_MERCHANT_SALT,
      },
    });
    const lastLine = stdout.trim().split("\n").pop() || "{}";
    const result = JSON.parse(lastLine);
    // The CLI now catches gateway errors and exits 0 with a clean
    // {"error": "..."} payload instead of crashing with a stack trace --
    // real bug found live-testing this: that used to mean `res.ok` was
    // true here even on failure, which the frontend's `if (!res.ok) throw`
    // check silently missed (no error shown, no success shown either).
    if (result.error) {
      return NextResponse.json(result, { status: 422 });
    }
    return NextResponse.json(result);
  } catch (e) {
    const err = e as { stderr?: string; message?: string };
    return NextResponse.json({ error: (err.stderr || err.message || "Subscription creation failed").trim() }, { status: 422 });
  }
}
