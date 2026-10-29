import { NextRequest, NextResponse } from "next/server";
import { suggestHsn } from "@/lib/ai-studio/local-adapters";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return NextResponse.json({ ...suggestHsn(String(body.description || "")), source: "local-adapter" });
}
