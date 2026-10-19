import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { authenticatedUser } from "@/lib/payment/auth";
import { verifySignature } from "@/lib/payment/signatures";
import { validatedPaidOrder } from "@/lib/payment/validate-order";
import { grantEntitlement } from "@/lib/payment/entitlement";

export const runtime = "nodejs";
const schema = z.object({ razorpay_order_id: z.string().min(1), razorpay_payment_id: z.string().min(1), razorpay_signature: z.string().min(1) });

export async function POST(request: NextRequest) {
  const user = await authenticatedUser(request);
  if (!user) return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  const parsed = schema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: "Invalid payment response" }, { status: 422 });
  const secret = process.env.RAZORPAY_KEY_SECRET;
  if (!secret) return NextResponse.json({ error: "Payment verification is unavailable" }, { status: 503 });
  const body = parsed.data;
  if (!verifySignature(`${body.razorpay_order_id}|${body.razorpay_payment_id}`, body.razorpay_signature, secret)) {
    return NextResponse.json({ error: "Invalid payment signature" }, { status: 400 });
  }
  try {
    const { purchase } = await validatedPaidOrder(body.razorpay_order_id);
    if (purchase.user_id !== user.id) return NextResponse.json({ error: "Payment does not belong to this account" }, { status: 403 });
    const result = await grantEntitlement(body.razorpay_order_id, body.razorpay_payment_id, user.id, purchase.tier, user.email);
    return NextResponse.json({ activated: true, ...result });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Payment validation failed" }, { status: 422 });
  }
}
