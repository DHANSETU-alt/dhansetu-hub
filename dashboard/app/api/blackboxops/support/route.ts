import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd(), "..");

// Customer-facing Support Bot -- deliberately SEPARATE from
// api/blackboxops/chat/route.ts (the founder's own internal ops
// assistant, which pulls his live task/initiative snapshot). This route
// must never import or call that snapshot logic: a site visitor asking
// a question has no business seeing internal business data. See
// orchestrator/support_bot.py's module docstring for the same rule on
// the backend side -- enforced in two places on purpose, not just one.
export async function POST(req: NextRequest) {
  const body = await req.json();
  const message = String(body.message || "").trim();
  const email = body.email ? String(body.email).trim() : undefined;
  const name = body.name ? String(body.name).trim() : undefined;

  const args = ["-m", "orchestrator.cli", "--support-bot-ask", message || " "];
  if (email) args.push("--support-email", email);
  if (name) args.push("--support-name", name);

  try {
    const { stdout } = await execFileAsync("python3", args, { cwd: PROJECT_ROOT, timeout: 60_000 });
    const lastLine = stdout.trim().split("\n").pop() || "{}";
    const result = JSON.parse(lastLine);
    return NextResponse.json(result);
  } catch (e) {
    const err = e as { stderr?: string; message?: string; killed?: boolean };
    if (err.killed) {
      return NextResponse.json({ error: "That took too long -- try a shorter question." }, { status: 504 });
    }
    return NextResponse.json({ error: (err.stderr || err.message || "Something went wrong.").trim() }, { status: 500 });
  }
}
