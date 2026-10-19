import { NextResponse } from "next/server";

const API_BASE = process.env.API_BASE || process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8787";

// Server-side proxy for founder command submission -- same PNA reason as
// state/route.ts. This is the one write path in Command Center: a real
// command submitted here goes through the real pa_angella.refine_and_send_to_ceo
// pipeline server-side (orchestrator/api.py's /api/command-center/submit),
// creating real task rows -- this route only relays it, it does not
// short-circuit or mock the dispatch.
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const text = searchParams.get("text") || "";
  const token = searchParams.get("token") || "";
  const headers: Record<string, string> = token ? { "X-Shakthi-Token": token } : {};

  if (!text.trim()) {
    return NextResponse.json({ error: "empty command" }, { status: 400 });
  }

  try {
    const res = await fetch(`${API_BASE}/api/command-center/submit?text=${encodeURIComponent(text)}`, {
      cache: "no-store",
      headers,
    });
    if (!res.ok) {
      const body = await res.text();
      return NextResponse.json({ error: `backend returned ${res.status}: ${body}` }, { status: 502 });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "submit failed" }, { status: 502 });
  }
}
