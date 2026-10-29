import { NextRequest, NextResponse } from "next/server";
import { analyzeExpense } from "@/lib/ai-studio/local-adapters";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return NextResponse.json({ ...analyzeExpense(body), source: "local-adapter" });
}
