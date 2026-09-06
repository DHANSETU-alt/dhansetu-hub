import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd(), "..");

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { name, symbol, ruleType, params } = body;

  if (!name || !symbol || !ruleType || !params) {
    return NextResponse.json({ error: "name, symbol, ruleType, and params are required" }, { status: 400 });
  }

  try {
    const { stdout } = await execFileAsync(
      "python3",
      ["-m", "orchestrator.cli", "--strategy-add", "--strategy-name", name, "--strategy-symbol", symbol,
       "--strategy-rule-type", ruleType, "--strategy-params", JSON.stringify(params)],
      { cwd: PROJECT_ROOT, timeout: 15_000 }
    );
    const result = JSON.parse(stdout.trim().split("\n").pop() || "{}");
    if (result.error) return NextResponse.json(result, { status: 422 });
    return NextResponse.json(result);
  } catch (e) {
    const err = e as { stderr?: string; message?: string };
    return NextResponse.json({ error: (err.stderr || err.message || "Failed to create strategy.").trim() }, { status: 500 });
  }
}
