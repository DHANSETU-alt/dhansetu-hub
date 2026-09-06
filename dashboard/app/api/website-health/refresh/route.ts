import { NextResponse } from "next/server";

const API_BASE = process.env.API_BASE || process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8787";

// Server-side proxy for the "REFRESH NOW" button -- the client component
// can't call the Python API directly: a real browser fetch from
// localhost:3000 to 127.0.0.1:8787 gets killed by Chrome's Private
// Network Access preflight, since orchestrator/api.py's stdlib
// http.server only implements do_GET (no OPTIONS handler, confirmed via
// a real 501 on a manual OPTIONS request). Every other page in this app
// avoids this by fetching server-side in a Next.js Server Component
// (Node has no CORS/PNA restriction); this is the one page with a
// client-triggered write, so it needs the same server-side-fetch escape
// hatch blackboxops/chat/route.ts already uses for backendIsUp().
export async function GET() {
  try {
    const [sitesRes, incidentsRes] = await Promise.all([
      fetch(`${API_BASE}/api/website-health/refresh`, { cache: "no-store" }),
      fetch(`${API_BASE}/api/website-health/incidents`, { cache: "no-store" }),
    ]);
    if (!sitesRes.ok || !incidentsRes.ok) {
      return NextResponse.json({ error: "backend returned a non-200 response" }, { status: 502 });
    }
    const sitesData = await sitesRes.json();
    const incidentsData = await incidentsRes.json();
    return NextResponse.json({ sites: sitesData.sites, incidents: incidentsData.incidents });
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "refresh failed" }, { status: 502 });
  }
}
