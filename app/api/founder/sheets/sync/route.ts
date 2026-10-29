import { NextResponse } from "next/server";
import { requireFounder } from "@/lib/auth/founder";
import { readFounderData } from "@/lib/founder/dashboard-data";
import { syncFounderSheet } from "@/lib/google/founder-sheets";

export const dynamic = "force-dynamic";

function sameOrigin(request: Request) {
  const origin = request.headers.get("origin");
  // This endpoint mutates a private founder Sheet.  Do not accept browser
  // requests that omit Origin; the founder session alone is not a CSRF proof.
  if (!origin) return false;
  const allowed = new Set<string>([new URL(request.url).origin]);
  if (process.env.NEXT_PUBLIC_APP_URL) {
    try { allowed.add(new URL(process.env.NEXT_PUBLIC_APP_URL).origin); } catch { /* invalid optional config is ignored */ }
  }
  return allowed.has(origin);
}

export async function POST(request: Request) {
  const access = await requireFounder();
  if (!access.user) return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  if (!access.allowed) return NextResponse.json({ error: "Founder access required" }, { status: 403 });
  if (!sameOrigin(request)) return NextResponse.json({ error: "Cross-origin request denied" }, { status: 403 });

  try {
    const data = await readFounderData();
    const result = await syncFounderSheet(data);
    return NextResponse.json(
      { ok: true, syncedAt: new Date().toISOString(), tabs: result.tabs, rowsWritten: result.rowsWritten },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch {
    console.error("founder_sheets_sync_failed");
    return NextResponse.json({ error: "Founder Sheets sync unavailable" }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
}
