import { NextRequest, NextResponse } from "next/server";
import { verifySignature } from "@/lib/payment/signatures";
import { validatedPaidOrder } from "@/lib/payment/validate-order";
import { grantEntitlement, revokeEntitlement } from "@/lib/payment/entitlement";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  const rawBody = await request.text();
  const secret = process.env.RAZORPAY_WEBHOOK_SECRET;
  if (!secret || !verifySignature(rawBody, request.headers.get("x-razorpay-signature"), secret)) {
    return NextResponse.json({ error: "Invalid webhook signature" }, { status: 401 });
  }
  let payload: { event?: string; payload?: {
    payment?: { entity?: { id?: string; order_id?: string } };
    order?: { entity?: { id?: string } };
    refund?: { entity?: { id?: string; payment_id?: string; amount?: number | string } };
  } };
  try { payload = JSON.parse(rawBody); } catch { return NextResponse.json({ error: "Invalid JSON" }, { status: 400 }); }
  if (payload.event === "refund.processed") {
    const refund = payload.payload?.refund?.entity;
    const paymentId = refund?.payment_id ?? payload.payload?.payment?.entity?.id;
    const amountPaise = Number(refund?.amount);
    if (!refund?.id || !paymentId || !Number.isSafeInteger(amountPaise) || amountPaise <= 0) {
      return NextResponse.json({ error: "Missing refund identifiers" }, { status: 422 });
    }
    try {
      const result = await revokeEntitlement(paymentId, refund.id, amountPaise);
      return NextResponse.json({ received: true, ...result });
    } catch (error) {
      return NextResponse.json({ error: error instanceof Error ? error.message : "Refund reconciliation failed" }, { status: 422 });
    }
  }
  if (payload.event !== "payment.captured" && payload.event !== "order.paid") return NextResponse.json({ received: true });
  const paymentId = payload.payload?.payment?.entity?.id;
  const orderId = payload.payload?.payment?.entity?.order_id ?? payload.payload?.order?.entity?.id;
  if (!paymentId || !orderId) return NextResponse.json({ error: "Missing payment identifiers" }, { status: 422 });
  try {
    const { purchase } = await validatedPaidOrder(orderId);
    const result = await grantEntitlement(orderId, paymentId, purchase.user_id, purchase.tier);
    return NextResponse.json({ received: true, ...result });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Payment validation failed" }, { status: 422 });
  }
}
