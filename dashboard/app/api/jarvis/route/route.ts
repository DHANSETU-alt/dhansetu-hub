import { NextResponse } from "next/server";

const API_BASE = process.env.API_BASE || process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8787";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const text = searchParams.get("text") || "";
  if (!text.trim()) return NextResponse.json({ error: "empty mission" }, { status: 400 });
  try {
    const response = await fetch(`${API_BASE}/api/jarvis/route?text=${encodeURIComponent(text)}`, { cache: "no-store" });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "routing preview failed" }, { status: 502 });
  }
}
