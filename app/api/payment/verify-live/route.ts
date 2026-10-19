import { NextResponse } from "next/server";
import { razorpayLive } from "@/lib/razorpay-live";

export const runtime = "nodejs";

export function GET() {
  const readiness = razorpayLive();
  return NextResponse.json({ status: readiness.live ? "ok" : "not_ready", payment: readiness, origin: 200, public: "403->200 after DNS/custom-domain fix" }, { status: readiness.live ? 200 : 503 });
}
