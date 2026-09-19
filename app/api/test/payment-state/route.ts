import { NextRequest, NextResponse } from "next/server";
import { mutateTestOrder, resetTestStore, testMode, testSnapshot } from "@/lib/payment/test-store";
import { isTierId } from "@/lib/payment/tiers";

export async function GET() {
  if (!testMode()) return new NextResponse(null, { status: 404 });
  return NextResponse.json(testSnapshot());
}
export async function DELETE() {
  if (!testMode()) return new NextResponse(null, { status: 404 });
  resetTestStore(); return NextResponse.json({ reset: true });
}
export async function PATCH(request: NextRequest) {
  if (!testMode()) return new NextResponse(null, { status: 404 });
  const body = await request.json();
  mutateTestOrder(body.orderId, { amount_paise: typeof body.amount === "number" ? body.amount : undefined, tier: isTierId(body.tier) ? body.tier : undefined });
  return NextResponse.json({ updated: true });
}
