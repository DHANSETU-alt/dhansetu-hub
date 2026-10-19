import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd(), "..");
const API_BASE = process.env.API_BASE || process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8787";

// Real, honest online/offline check -- the founder's own requirement:
// "if system off bot sleep," not a bot that pretends to be available when
// the backend (Ollama + the orchestrator) genuinely isn't running. Short
// timeout on purpose: this must fail fast, not hang the widget.
async function backendIsUp(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

async function dashboardSnapshot(): Promise<string> {
  try {
    const [tasksRes, initiativesRes] = await Promise.all([
      fetch(`${API_BASE}/api/tasks`, { cache: "no-store", signal: AbortSignal.timeout(3000) }),
      fetch(`${API_BASE}/api/initiatives`, { cache: "no-store", signal: AbortSignal.timeout(3000) }),
    ]);
    if (!tasksRes.ok || !initiativesRes.ok) return "DASHBOARD SNAPSHOT: unavailable";
    const tasks = await tasksRes.json();
    const initiatives = await initiativesRes.json();
    const incompleteTasks = (tasks.tasks || []).filter((t: any) => !["completed", "done", "cancelled"].includes(String(t.status).toLowerCase())).slice(0, 20);
    const incompleteInitiatives = (initiatives.initiatives || []).filter((i: any) => !["completed", "done", "cancelled"].includes(String(i.status).toLowerCase())).slice(0, 12);
    return `DASHBOARD SNAPSHOT (read-only, collected now):\nTASKS: ${JSON.stringify(incompleteTasks)}\nINITIATIVES: ${JSON.stringify(incompleteInitiatives)}\nCOUNTS: ${JSON.stringify(tasks.counts || {})}`;
  } catch {
    return "DASHBOARD SNAPSHOT: unavailable";
  }
}

export async function GET() {
  return NextResponse.json({ up: await backendIsUp() });
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const message = String(body.message || "").trim();
  if (!message) return NextResponse.json({ error: "message is required" }, { status: 400 });

  if (!(await backendIsUp())) {
    return NextResponse.json({ error: "sleeping", sleeping: true }, { status: 503 });
  }

  try {
    // Real local-model call (sales agent) -- can genuinely take a while
    // under load (this machine has hit real Ollama contention before),
    // so real headroom, not a snappy-feeling short timeout that just
    // fails under normal load.
    const snapshot = await dashboardSnapshot();
    const guidedMessage = `${snapshot}\n\nFOUNDER MESSAGE:\n${message}\n\nReview the snapshot first. Respond as Shakthi_Agent, the SHAKTHI_OS delivery partner: give the highest-priority unfinished item, a finish plan, blockers, and a clearly labeled FOUNDER ACTION REQUIRED list. Preserve the founder's intent.`;
    const { stdout } = await execFileAsync(
      "python3", ["-m", "orchestrator.cli", "--chat-message", guidedMessage, "--chat-agent", "pa_angella"],
      { cwd: PROJECT_ROOT, timeout: 110_000 }
    );
    const parsed = JSON.parse(stdout.trim().split("\n").pop() || "{}");
    if (!parsed.reply) return NextResponse.json({ error: "No reply generated." }, { status: 502 });
    return NextResponse.json({ reply: parsed.reply });
  } catch (e) {
    const err = e as { stderr?: string; message?: string; killed?: boolean };
    if (err.killed) {
      return NextResponse.json({ error: "That took too long to answer -- try a shorter question." }, { status: 504 });
    }
    return NextResponse.json({ error: (err.stderr || err.message || "Something went wrong.").trim() }, { status: 500 });
  }
}
