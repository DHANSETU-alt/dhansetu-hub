import { NextRequest, NextResponse } from "next/server";
import { parseForm16 } from "@/lib/ai-studio/local-adapters";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return NextResponse.json({ ...parseForm16(String(body.rawText || "")), source: "local-adapter" });
}
