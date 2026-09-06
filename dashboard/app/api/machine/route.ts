import { NextResponse } from "next/server";

const API_BASE = process.env.API_BASE || process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8787";

// Server-side proxy so the sidebar's MachineBadge (a client component) can
// ask "which machine is this" without hitting the Private Network Access
// preflight a direct browser fetch to :8787 runs into -- same escape hatch
// documented in app/api/website-health/refresh/route.ts.
export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
    if (!res.ok) return NextResponse.json({ hostname: null }, { status: 502 });
    const data = await res.json();
    return NextResponse.json({ hostname: data.hostname ?? null });
  } catch {
    return NextResponse.json({ hostname: null }, { status: 502 });
  }
}
