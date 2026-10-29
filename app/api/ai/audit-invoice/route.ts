import { NextRequest, NextResponse } from "next/server";
import { auditInvoice } from "@/lib/ai-studio/local-adapters";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return NextResponse.json({ ...auditInvoice(body.invoice || {}), source: "local-adapter" });
}
