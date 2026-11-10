import { createAdminSupabase } from "@/lib/supabase/admin";
import { grantTestEntitlement, revokeTestEntitlement, testEntitled, testMode, testPlan } from "./test-store";
import { isTierId, type TierId } from "./tiers";
import { purchaseCoversTier } from "./purchase-access";
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

export async function revokeEntitlement(paymentId: string, refundId: string, amountPaise: number) {
  if (testMode()) return revokeTestEntitlement(paymentId, refundId, amountPaise);
  const { data, error } = await createAdminSupabase().rpc("revoke_lifetime_entitlement", {
    p_payment_id: paymentId, p_refund_id: refundId, p_refund_amount_paise: amountPaise,
  });
  if (error) throw new Error(`Entitlement refund reconciliation failed: ${error.message}`);
  const row = Array.isArray(data) ? data[0] : data;
  return { revoked: Boolean(row?.revoked), idempotent: Boolean(row?.idempotent), partial: Boolean(row?.partial) };
}

export async function hasEntitlement(userId: string) {
  if (testMode()) return testEntitled(userId);
  const { data, error } = await createAdminSupabase().from("profiles").select("plan").eq("id", userId).maybeSingle();
  if (error) throw new Error(`Could not read entitlement: ${error.message}`);
  return Boolean(data?.plan && data.plan !== "free");
}

export async function hasTierAccess(userId: string, requestedTier: TierId) {
  const plan = testMode()
    ? testPlan(userId)
    : await readProductionPlan(userId);
  return Boolean(plan && purchaseCoversTier(plan, requestedTier));
}

async function readProductionPlan(userId: string): Promise<TierId | null> {
  const { data, error } = await createAdminSupabase().from("profiles").select("plan").eq("id", userId).maybeSingle();
  if (error) throw new Error(`Could not read entitlement: ${error.message}`);
  return isTierId(data?.plan) ? data.plan : null;
}
