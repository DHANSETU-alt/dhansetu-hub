import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd(), "..");

export async function GET(req: NextRequest) {
  const email = req.nextUrl.searchParams.get("email")?.trim().toLowerCase();
  if (!email) return NextResponse.json({ error: "email is required" }, { status: 400 });

  try {
    const { stdout } = await execFileAsync(
      "python3", ["-m", "orchestrator.cli", "--pricing-check", "--email", email, "--product", "peopledesk"],
      { cwd: PROJECT_ROOT, timeout: 15_000 }
    );
    const result = JSON.parse(stdout.trim().split("\n").pop() || "{}");
    return NextResponse.json(result);
  } catch (e) {
    const err = e as { stderr?: string; message?: string };
    return NextResponse.json({ error: (err.stderr || err.message || "Access check failed.").trim() }, { status: 500 });
  }
}
