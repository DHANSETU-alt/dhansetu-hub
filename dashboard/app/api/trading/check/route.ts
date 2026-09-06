import { NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd(), "..");

export async function POST() {
  try {
    const { stdout } = await execFileAsync(
      "python3", ["-m", "orchestrator.cli", "--trading-check"],
      { cwd: PROJECT_ROOT, timeout: 20_000 }
    );
    const result = JSON.parse(stdout.trim().split("\n").pop() || "{}");
    return NextResponse.json(result);
  } catch (e) {
    const err = e as { stderr?: string; message?: string };
    return NextResponse.json({ error: (err.stderr || err.message || "Signal check failed.").trim() }, { status: 500 });
  }
}
