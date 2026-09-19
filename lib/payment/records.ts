import { createAdminSupabase } from "@/lib/supabase/admin";
import { testMode, testPurchaseByOrder, testPurchases, testRateLimit } from "./test-store";
import type { Purchase } from "./types";
import type { TierId } from "./tiers";

export async function checkoutRateAllowed(key: string) {
  if (testMode()) return testRateLimit(key);
  const { data, error } = await createAdminSupabase().rpc("check_checkout_rate_limit", { p_key: key, p_limit: 8, p_window_seconds: 60 });
  if (error) throw new Error(`Rate limit check failed: ${error.message}`);
  return Boolean(data);
}

export async function seatsRemaining(tier: TierId) {
  if (testMode()) {
    const { testSnapshot } = await import("./test-store");
    const sold = Number(testSnapshot().seats[tier] ?? 0);
    const { TIERS } = await import("./tiers");
    return Math.max(0, TIERS[tier].seatLimit - sold);
  }
  const { data, error } = await createAdminSupabase().from("tier_seats").select("seat_limit,seats_sold").eq("tier", tier).single();
  if (error) throw new Error(`Could not check seats: ${error.message}`);
  return Math.max(0, data.seat_limit - data.seats_sold);
}

export async function saveCreatedPurchase(input: { userId: string; tier: TierId; orderId: string; amount: number; currency: string; consentedAt: string; consentIp: string; termsVersion: string }) {
  if (testMode()) return;
  const { error } = await createAdminSupabase().from("purchases").insert({
    user_id: input.userId, tier: input.tier, razorpay_order_id: input.orderId,
    amount_paise: input.amount, currency: input.currency, status: "created",
    consented_at: input.consentedAt, consent_ip: input.consentIp, terms_version: input.termsVersion,
  });
  if (error) throw new Error(`Could not save purchase: ${error.message}`);
}

export async function purchaseByOrder(orderId: string): Promise<Purchase | null> {
  if (testMode()) return testPurchaseByOrder(orderId);
  const { data, error } = await createAdminSupabase().from("purchases").select("*").eq("razorpay_order_id", orderId).maybeSingle();
  if (error) throw new Error(`Could not read purchase: ${error.message}`);
  return data as Purchase | null;
}

export async function purchasesForUser(userId: string) {
  if (testMode()) return testPurchases(userId);
  const { data, error } = await createAdminSupabase().from("purchases").select("id,tier,razorpay_order_id,razorpay_payment_id,amount_paise,currency,status,created_at,paid_at").eq("user_id", userId).order("created_at", { ascending: false });
  if (error) throw new Error(`Could not list purchases: ${error.message}`);
  return data;
}
