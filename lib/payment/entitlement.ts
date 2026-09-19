import { createAdminSupabase } from "@/lib/supabase/admin";
import { grantTestEntitlement, testEntitled, testMode } from "./test-store";
import type { TierId } from "./tiers";
import { sendReceipt } from "./receipt";

export async function grantEntitlement(orderId: string, paymentId: string, userId: string, tier: TierId, email = "") {
  const result = testMode()
    ? await grantTestEntitlement(orderId, paymentId, userId, tier)
    : await grantProduction(orderId, paymentId, userId, tier);
  let receiptEmail = email;
  if (result.granted && !receiptEmail && !testMode()) {
    const { data } = await createAdminSupabase().auth.admin.getUserById(userId);
    receiptEmail = data.user?.email ?? "";
  }
  if (result.granted && receiptEmail) {
    await sendReceipt({ email: receiptEmail, orderId, paymentId, tier, paidAt: new Date().toISOString() }).catch((error) =>
      console.warn("[receipt] delivery failed", { orderId, message: error instanceof Error ? error.message : "unknown" }),
    );
  }
  return result;
}

async function grantProduction(orderId: string, paymentId: string, userId: string, tier: TierId) {
  const { data, error } = await createAdminSupabase().rpc("grant_lifetime_entitlement", {
    p_order_id: orderId, p_payment_id: paymentId, p_user_id: userId, p_tier: tier,
  });
  if (error) throw new Error(`Entitlement grant failed: ${error.message}`);
  const row = Array.isArray(data) ? data[0] : data;
  return { granted: Boolean(row?.granted), idempotent: Boolean(row?.idempotent) };
}

export async function hasEntitlement(userId: string) {
  if (testMode()) return testEntitled(userId);
  const { data, error } = await createAdminSupabase().from("profiles").select("plan").eq("id", userId).maybeSingle();
  if (error) throw new Error(`Could not read entitlement: ${error.message}`);
  return data?.plan === "founding_lifetime";
}
