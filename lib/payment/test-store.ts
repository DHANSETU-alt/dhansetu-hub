import type { Purchase, RazorpayOrder } from "./types";
import { TIERS, type TierId } from "./tiers";

type TestState = {
  purchases: Map<string, Purchase>;
  paymentIds: Set<string>;
  refundIds: Set<string>;
  plans: Map<string, TierId>;
  seats: Map<TierId, number>;
  rate: Map<string, number[]>;
};

declare global {
  var __dhansetuPaymentTestState: TestState | undefined;
}

const state = globalThis.__dhansetuPaymentTestState ?? {
  purchases: new Map<string, Purchase>(),
  paymentIds: new Set<string>(),
  refundIds: new Set<string>(),
  plans: new Map<string, TierId>(),
  seats: new Map<TierId, number>(),
  rate: new Map<string, number[]>(),
};
globalThis.__dhansetuPaymentTestState = state;
let lock = Promise.resolve();

export function testMode() {
  return process.env.PAYMENT_FLOW_TEST_MODE === "1" && process.env.NODE_ENV !== "production";
}

export function resetTestStore() {
  state.purchases.clear(); state.paymentIds.clear(); state.refundIds.clear(); state.plans.clear(); state.seats.clear(); state.rate.clear();
}

export function testSnapshot() {
  return { purchases: Array.from(state.purchases.values()), plans: Object.fromEntries(state.plans), seats: Object.fromEntries(state.seats) };
}

export function testRateLimit(key: string, limit = 8) {
  const now = Date.now();
  const recent = (state.rate.get(key) ?? []).filter((time) => now - time < 60_000);
  if (recent.length >= limit) return false;
  recent.push(now); state.rate.set(key, recent); return true;
}

export function createTestOrder(userId: string, tier: TierId, consent: Omit<Purchase, "id" | "user_id" | "tier" | "razorpay_order_id" | "razorpay_payment_id" | "amount_paise" | "currency" | "status" | "created_at" | "paid_at">) {
  const id = `order_test_${crypto.randomUUID()}`;
  const now = new Date().toISOString();
  const purchase: Purchase = { id: crypto.randomUUID(), user_id: userId, tier, razorpay_order_id: id, razorpay_payment_id: null, amount_paise: TIERS[tier].amountPaise, currency: "INR", status: "created", created_at: now, paid_at: null, ...consent };
  state.purchases.set(id, purchase);
  return { id, amount: purchase.amount_paise, currency: purchase.currency, status: "created", notes: { user_id: userId, tier } } satisfies RazorpayOrder;
}

export function getTestOrder(orderId: string) {
  const p = state.purchases.get(orderId);
  return p ? { id: orderId, amount: p.amount_paise, currency: p.currency, status: p.status, notes: { user_id: p.user_id, tier: p.tier } } satisfies RazorpayOrder : null;
}

export function mutateTestOrder(orderId: string, values: Partial<Pick<Purchase, "amount_paise" | "tier" | "currency">>) {
  const row = state.purchases.get(orderId);
  if (!row) return;
  if (values.amount_paise !== undefined) row.amount_paise = values.amount_paise;
  if (values.currency !== undefined) row.currency = values.currency;
  if (values.tier !== undefined) row.tier = values.tier;
}

export async function grantTestEntitlement(orderId: string, paymentId: string, userId: string, tier: TierId) {
  let release!: () => void;
  const previous = lock;
  lock = new Promise<void>((resolve) => { release = resolve; });
  await previous;
  try {
    const purchase = state.purchases.get(orderId);
    if (!purchase || purchase.user_id !== userId || purchase.tier !== tier) throw new Error("Purchase identity mismatch");
    if (purchase.status === "paid") return { granted: false, idempotent: true };
    if (purchase.status !== "created") throw new Error("Purchase is not eligible for activation");
    if (state.paymentIds.has(paymentId)) return { granted: false, idempotent: true };
    const sold = state.seats.get(tier) ?? 0;
    if (sold >= TIERS[tier].seatLimit) throw new Error("Tier is sold out");
    purchase.status = "paid"; purchase.razorpay_payment_id = paymentId; purchase.paid_at = new Date().toISOString();
    state.paymentIds.add(paymentId); state.seats.set(tier, sold + 1); state.plans.set(userId, tier);
    return { granted: true, idempotent: false };
  } finally { release(); }
}

export async function revokeTestEntitlement(paymentId: string, refundId: string, amountPaise: number) {
  if (state.refundIds.has(refundId)) return { revoked: false, idempotent: true, partial: false };
  const purchase = Array.from(state.purchases.values()).find((item) => item.razorpay_payment_id === paymentId);
  if (!purchase || !["paid", "partially_refunded", "refunded"].includes(purchase.status)) throw new Error("Payment is not eligible for refund reconciliation");
  const refunded = (purchase.refunded_amount_paise ?? 0) + amountPaise;
  if (!Number.isSafeInteger(amountPaise) || amountPaise <= 0 || refunded > purchase.amount_paise) throw new Error("Refund total exceeds payment amount");
  state.refundIds.add(refundId);
  purchase.refunded_amount_paise = refunded;
  if (refunded < purchase.amount_paise) { purchase.status = "partially_refunded"; return { revoked: false, idempotent: false, partial: true }; }
  if (purchase.status === "refunded") return { revoked: false, idempotent: true, partial: false };
  purchase.status = "refunded"; purchase.refunded_at = new Date().toISOString();
  state.seats.set(purchase.tier, Math.max(0, (state.seats.get(purchase.tier) ?? 0) - 1));
  const remaining = Array.from(state.purchases.values()).filter((item) => item.user_id === purchase.user_id && ["paid", "partially_refunded"].includes(item.status));
  const next = remaining.sort((a, b) => (a.tier === "all_access" ? -1 : 0) - (b.tier === "all_access" ? -1 : 0))[0];
  if (next) state.plans.set(purchase.user_id, next.tier); else state.plans.delete(purchase.user_id);
  return { revoked: true, idempotent: false, partial: false };
}

export function testEntitled(userId: string) { return state.plans.has(userId); }
export function testPlan(userId: string) { return state.plans.get(userId) ?? null; }
export function testPurchases(userId: string) { return Array.from(state.purchases.values()).filter((p) => p.user_id === userId); }
export function testPurchaseByOrder(orderId: string) { return state.purchases.get(orderId) ?? null; }
