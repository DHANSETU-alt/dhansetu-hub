import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd(), "..");

async function runCli(args: string[]): Promise<Record<string, unknown>> {
  const { stdout } = await execFileAsync("python3", ["-m", "orchestrator.cli", ...args], { cwd: PROJECT_ROOT, timeout: 20_000 });
  return JSON.parse(stdout.trim().split("\n").pop() || "{}");
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const ownerEmail = String(body.ownerEmail || "").trim().toLowerCase();
  const name = String(body.name || "").trim();
  const payType = body.payType === "monthly" ? "monthly" : "daily";

  if (!ownerEmail) return NextResponse.json({ error: "ownerEmail is required" }, { status: 400 });
  if (!name) return NextResponse.json({ error: "Staff name is required" }, { status: 400 });

  // Real gate -- PeopleDesk has zero free uses (see pricing.py), so this
  // always requires an active subscription. Same layering as PDF
  // Studio's process route: the gate lives here, not inside peopledesk.py.
  const access = await runCli(["--pricing-check", "--email", ownerEmail, "--product", "peopledesk"]);
  if (access.error) return NextResponse.json({ error: access.error as string }, { status: 500 });
  if (!access.allowed) {
    return NextResponse.json(
      { error: access.reason, requiresPayment: true, priceInr: access.price_inr, label: access.label },
      { status: 402 }
    );
  }

  const args = [
    "--peopledesk-add-staff", "--owner-email", ownerEmail, "--staff-name", name,
    "--staff-pay-type", payType,
  ];
  if (body.role) args.push("--staff-role", String(body.role));
  if (body.phone) args.push("--staff-phone", String(body.phone));
  if (body.joinDate) args.push("--staff-join-date", String(body.joinDate));
  if (payType === "daily") args.push("--staff-daily-wage", String(body.dailyWageInr || ""));
  else args.push("--staff-monthly-salary", String(body.monthlySalaryInr || ""));

  try {
    const result = await runCli(args);
    if (result.error) return NextResponse.json(result, { status: 422 });
    return NextResponse.json(result);
  } catch (e) {
    const err = e as { stderr?: string; message?: string };
    return NextResponse.json({ error: (err.stderr || err.message || "Failed to add staff.").trim() }, { status: 500 });
  }
}
