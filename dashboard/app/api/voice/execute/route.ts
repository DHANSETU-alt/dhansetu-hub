import { NextResponse } from "next/server";

const API_BASE = process.env.API_BASE || process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8787";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const text = (searchParams.get("text") || "").trim();
  const language = searchParams.get("language") || "en";
  if (!text) return NextResponse.json({ error: "empty transcript" }, { status: 400 });
  try {
    const qs = new URLSearchParams({ text, language });
    const response = await fetch(`${API_BASE}/api/voice/execute?${qs.toString()}`, { cache: "no-store" });
    const data = await response.json();
    return NextResponse.json(data, { status: response.ok ? 200 : 502 });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "voice execution failed" }, { status: 502 });
  }
}
