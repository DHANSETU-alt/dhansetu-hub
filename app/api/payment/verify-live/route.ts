import { NextResponse } from "next/server";
import { razorpayLive } from "@/lib/razorpay-live";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export function GET() {
  const readiness = razorpayLive();
  return NextResponse.json({
    status: readiness.configured ? "configured" : "not_ready",
    payment: readiness,
    verification: "Configuration check only. A captured payment and signed webhook must be verified separately.",
  }, { status: readiness.configured ? 200 : 503 });
}
