import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { authenticatedUser } from "@/lib/payment/auth";
import { TIERS, isTierId } from "@/lib/payment/tiers";
import { checkoutRateAllowed, saveCreatedPurchase, seatsRemaining } from "@/lib/payment/records";
import { createOrder, razorpayKeyId } from "@/lib/payment/razorpay";

export const runtime = "nodejs";
const inputSchema = z.object({ tier: z.string(), consent: z.literal(true) });

export async function POST(request: NextRequest) {
  const user = await authenticatedUser(request);
  if (!user) return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  if (!(await checkoutRateAllowed(`${user.id}:${ip}`))) return NextResponse.json({ error: "Too many checkout attempts" }, { status: 429 });
  const parsed = inputSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success || !isTierId(parsed.data.tier)) return NextResponse.json({ error: "Invalid tier or missing consent" }, { status: 422 });
  const tier = parsed.data.tier;
  if ((await seatsRemaining(tier)) < 1) return NextResponse.json({ error: "This tier is sold out" }, { status: 409 });
  const consent = { consented_at: new Date().toISOString(), consent_ip: ip, terms_version: process.env.PAYMENT_TERMS_VERSION ?? "2026-09-19" };
  const order = await createOrder({ userId: user.id, tier, amount: TIERS[tier].amountPaise, consent });
  await saveCreatedPurchase({ userId: user.id, tier, orderId: order.id, amount: TIERS[tier].amountPaise, currency: "INR", consentedAt: consent.consented_at, consentIp: ip, termsVersion: consent.terms_version });
  return NextResponse.json({ orderId: order.id, keyId: razorpayKeyId(), amount: TIERS[tier].amountPaise, currency: "INR", tier });
}
