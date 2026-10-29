import { NextRequest, NextResponse } from "next/server";
import { authenticatedUser } from "@/lib/payment/auth";
import { grantEntitlement, hasEntitlement } from "@/lib/payment/entitlement";
import { purchaseByOrder } from "@/lib/payment/records";
import { validatedPaidOrder } from "@/lib/payment/validate-order";
import { fetchCapturedPaymentId } from "@/lib/payment/razorpay";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  const user = await authenticatedUser(request);
  if (!user) return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  try {
    const orderId = request.nextUrl.searchParams.get("order");
    if (orderId) {
      const purchase = await purchaseByOrder(orderId);
      if (!purchase || purchase.user_id !== user.id) return NextResponse.json({ error: "Order not found" }, { status: 404 });
      if (purchase.status !== "paid") {
        // Retry the existing grant when callback/webhook delivery was interrupted.
        const { order } = await validatedPaidOrder(orderId);
        const paymentId = await fetchCapturedPaymentId(order);
        if (!paymentId) throw new Error("Capture pending");
        await grantEntitlement(orderId, paymentId, user.id, purchase.tier, user.email);
      }
    }
    return NextResponse.json({ active: await hasEntitlement(user.id), appUrl: process.env.NEXT_PUBLIC_APP_URL ?? "https://dhansetuhub.in" });
  } catch {
    return NextResponse.json({ active: false, pending: true, error: "Account verification is pending. Do not pay again." }, { status: 202 });
  }
}
