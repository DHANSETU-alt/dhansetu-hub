import type { Purchase, RazorpayOrder } from "./types";
import { TIERS, type TierId } from "./tiers";

type TestState = {
  purchases: Map<string, Purchase>;
  paymentIds: Set<string>;
  plans: Map<string, string>;
  seats: Map<TierId, number>;
  rate: Map<string, number[]>;
};

declare global {
  // eslint-disable-next-line no-var -- TypeScript global augmentation requires `var`.
  var __dhansetuPaymentTestState: TestState | undefined;
}

const state = globalThis.__dhansetuPaymentTestState ?? {
  purchases: new Map<string, Purchase>(),
  paymentIds: new Set<string>(),
  plans: new Map<string, string>(),
  seats: new Map<TierId, number>(),
  rate: new Map<string, number[]>(),
};
globalThis.__dhansetuPaymentTestState = state;
let lock = Promise.resolve();

export function testMode() {
  return process.env.PAYMENT_FLOW_TEST_MODE === "1" && process.env.NODE_ENV !== "production";
}

export function resetTestStore() {
  state.purchases.clear(); state.paymentIds.clear(); state.plans.clear(); state.seats.clear(); state.rate.clear();
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
  return p ? { id: orderId, amount: p.amount_paise, currency: p.currency, status: "paid", notes: { user_id: p.user_id, tier: p.tier } } satisfies RazorpayOrder : null;
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
    if (state.paymentIds.has(paymentId)) return { granted: false, idempotent: true };
    const sold = state.seats.get(tier) ?? 0;
    if (sold >= TIERS[tier].seatLimit) throw new Error("Tier is sold out");
    purchase.status = "paid"; purchase.razorpay_payment_id = paymentId; purchase.paid_at = new Date().toISOString();
    state.paymentIds.add(paymentId); state.seats.set(tier, sold + 1); state.plans.set(userId, "founding_lifetime");
    return { granted: true, idempotent: false };
  } finally { release(); }
}

export function testEntitled(userId: string) { return state.plans.has(userId); }
export function testPurchases(userId: string) { return Array.from(state.purchases.values()).filter((p) => p.user_id === userId); }
export function testPurchaseByOrder(orderId: string) { return state.purchases.get(orderId) ?? null; }
