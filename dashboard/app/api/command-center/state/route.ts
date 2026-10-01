import { NextResponse } from "next/server";

const API_BASE = process.env.API_BASE || process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8787";

// Server-side proxy for the Command Center's polling load() -- same reason
// as app/api/website-health/refresh/route.ts: a real browser fetch from
// localhost:3000 to 127.0.0.1:8787 gets killed by Chrome's Private Network
// Access preflight (orchestrator/api.py's stdlib http.server has no OPTIONS
// handler). Command Center is a client component (it needs live polling +
// a founder-typed command input, which a Server Component can't do), so
// unlike every read-only page in this app, it can't just fetch server-side
// at render time -- it needs this same escape hatch on every poll.
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const token = searchParams.get("token") || "";
  const headers: Record<string, string> = token ? { "X-Shakthi-Token": token } : {};

  try {
    const [tasksRes, logsRes, healthRes, decisionsRes] = await Promise.all([
      fetch(`${API_BASE}/api/tasks`, { cache: "no-store", headers }),
      fetch(`${API_BASE}/api/command-center/logs?limit=60`, { cache: "no-store", headers }),
      fetch(`${API_BASE}/api/agent-health`, { cache: "no-store", headers }),
      // Real "revise" decisions (see agents/ceo.yaml: "revise means the goal
      // is worth pursuing but is underspecified or risky as written") are
      // the one real, evidence-backed "needs founder attention" signal this
      // backend already produces -- not a fabricated approvals concept.
      fetch(`${API_BASE}/api/ceo/decisions?limit=30`, { cache: "no-store", headers }),
    ]);
    if (!tasksRes.ok) {
      return NextResponse.json({ error: "backend returned a non-200 response for /api/tasks" }, { status: 502 });
    }
    const tasksData = await tasksRes.json();
    const logsData = logsRes.ok ? await logsRes.json() : { events: [] };
    const healthData = healthRes.ok ? await healthRes.json() : { agents: [] };
    const decisionsData = decisionsRes.ok ? await decisionsRes.json() : { decisions: [] };
    return NextResponse.json({
      tasks: tasksData.tasks,
      events: logsData.events,
      agents: healthData.agents,
      decisions: decisionsData.decisions,
    });
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "state fetch failed" }, { status: 502 });
  }
}
