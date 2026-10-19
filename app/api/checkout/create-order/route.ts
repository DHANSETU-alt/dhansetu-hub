import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { authenticatedUser } from "@/lib/payment/auth";
import { TIERS, isTierId } from "@/lib/payment/tiers";
import { checkoutRateAllowed, purchasesForUser, saveCreatedPurchase, seatsRemaining } from "@/lib/payment/records";
import { purchaseCoversTier } from "@/lib/payment/purchase-access";
import { createOrder, fetchCapturedPaymentId, fetchOrder, razorpayKeyId } from "@/lib/payment/razorpay";

import { grantEntitlement } from "@/lib/payment/entitlement";

export const runtime = "nodejs";
const inputSchema = z.object({ tier: z.string(), consent: z.literal(true) });

export async function POST(request: NextRequest) {
  try {
    const user = await authenticatedUser(request);
    if (!user) return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
    if (!(await checkoutRateAllowed(`${user.id}:${ip}`))) return NextResponse.json({ error: "Too many checkout attempts" }, { status: 429 });
    const parsed = inputSchema.safeParse(await request.json().catch(() => null));
    if (!parsed.success || !isTierId(parsed.data.tier)) return NextResponse.json({ error: "Invalid tier or missing consent" }, { status: 422 });
    const tier = parsed.data.tier;
    const purchases = await purchasesForUser(user.id);
    const existing = purchases.find((purchase) => purchase.status === "paid" && isTierId(purchase.tier) && purchaseCoversTier(purchase.tier, tier));
    if (existing) return NextResponse.json({ existingAccess: true, orderId: existing.razorpay_order_id });
    // Reuse unresolved orders so a lost browser callback never starts a second charge.
    const pending = purchases.find((purchase) => purchase.status === "created" && purchase.tier === tier);
    if (pending) {
      const providerOrder = await fetchOrder(pending.razorpay_order_id);
      if (!providerOrder) throw new Error("Pending order could not be checked");
      if (providerOrder.amount !== TIERS[tier].amountPaise || providerOrder.currency !== "INR" || providerOrder.notes?.user_id !== user.id || providerOrder.notes?.tier !== tier) throw new Error("Pending order does not match purchase");
      if (providerOrder.status === "paid") {
        const paymentId = await fetchCapturedPaymentId(providerOrder);
        if (!paymentId) throw new Error("Captured payment is not yet available");
        await grantEntitlement(providerOrder.id, paymentId, user.id, tier, user.email);
        return NextResponse.json({ recovery: true, orderId: providerOrder.id });
      }
      return NextResponse.json({ orderId: providerOrder.id, keyId: razorpayKeyId(), amount: TIERS[tier].amountPaise, currency: "INR", tier });
    }
    if ((await seatsRemaining(tier)) < 1) return NextResponse.json({ error: "This tier is sold out" }, { status: 409 });
    const consent = { consented_at: new Date().toISOString(), consent_ip: ip, terms_version: process.env.PAYMENT_TERMS_VERSION ?? "2026-09-19" };
    const order = await createOrder({ userId: user.id, tier, amount: TIERS[tier].amountPaise, consent });
    await saveCreatedPurchase({ userId: user.id, tier, orderId: order.id, amount: TIERS[tier].amountPaise, currency: "INR", consentedAt: consent.consented_at, consentIp: ip, termsVersion: consent.terms_version });
    return NextResponse.json({ orderId: order.id, keyId: razorpayKeyId(), amount: TIERS[tier].amountPaise, currency: "INR", tier });
  } catch {
    return NextResponse.json({ error: "Checkout is temporarily unavailable. Please try again later. If you have already paid, do not pay again; check Billing or contact support." }, { status: 503 });
  }
}
