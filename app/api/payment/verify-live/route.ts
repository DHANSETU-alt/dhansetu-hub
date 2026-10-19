import { NextResponse } from "next/server";
import { razorpayLiveCheck } from "@/lib/razorpay-live-check";

export const runtime = "nodejs";

export function GET() {
  const readiness = razorpayLiveCheck();
  const ready = Object.values(readiness).every(Boolean);
  return NextResponse.json({ status: ready ? "ok" : "not_ready", payment: readiness }, { status: ready ? 200 : 503 });
}
