import { NextRequest, NextResponse } from "next/server";
import { reminderTone } from "@/lib/ai-studio/local-adapters";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return NextResponse.json({ whatsappMessage: reminderTone(body), source: "local-adapter" });
}
