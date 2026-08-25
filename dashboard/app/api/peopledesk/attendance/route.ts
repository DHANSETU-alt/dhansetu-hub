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
  const staffId = Number(body.staffId);
  const attendanceDate = String(body.attendanceDate || "").trim();
  const status = String(body.status || "").trim();

  if (!ownerEmail) return NextResponse.json({ error: "ownerEmail is required" }, { status: 400 });
  if (!staffId || !attendanceDate || !status) {
    return NextResponse.json({ error: "staffId, attendanceDate, and status are required" }, { status: 400 });
  }

  const access = await runCli(["--pricing-check", "--email", ownerEmail, "--product", "peopledesk"]);
  if (access.error) return NextResponse.json({ error: access.error as string }, { status: 500 });
  if (!access.allowed) {
    return NextResponse.json(
      { error: access.reason, requiresPayment: true, priceInr: access.price_inr, label: access.label },
      { status: 402 }
    );
  }

  try {
    const result = await runCli([
      "--peopledesk-mark-attendance", "--staff-id", String(staffId),
      "--attendance-date", attendanceDate, "--attendance-status", status,
    ]);
    if (result.error) return NextResponse.json(result, { status: 422 });
    return NextResponse.json(result);
  } catch (e) {
    const err = e as { stderr?: string; message?: string };
    return NextResponse.json({ error: (err.stderr || err.message || "Failed to mark attendance.").trim() }, { status: 500 });
  }
}
