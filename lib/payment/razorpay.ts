import Razorpay from "razorpay";
import type { RazorpayOrder } from "./types";
import { createTestOrder, getTestOrder, testMode } from "./test-store";
import type { TierId } from "./tiers";

function secrets() {
  const keyId = process.env.RAZORPAY_KEY_ID;
  const keySecret = process.env.RAZORPAY_KEY_SECRET;
  if (!keyId || !keySecret) throw new Error("Razorpay server configuration is missing");
  return { keyId, keySecret };
}

export function razorpayKeyId() { return secrets().keyId; }

export async function createOrder(input: { userId: string; tier: TierId; amount: number; consent: { consented_at: string; consent_ip: string; terms_version: string } }) {
  if (testMode()) return createTestOrder(input.userId, input.tier, input.consent);
  const { keyId, keySecret } = secrets();
  const client = new Razorpay({ key_id: keyId, key_secret: keySecret });
  const order = await client.orders.create({
    amount: input.amount,
    currency: "INR",
    receipt: `dh_${Date.now().toString(36)}_${crypto.randomUUID().slice(0, 8)}`,
    notes: { user_id: input.userId, tier: input.tier },
  });
  return order as unknown as RazorpayOrder;
}

export async function fetchOrder(orderId: string): Promise<RazorpayOrder | null> {
  if (testMode()) return getTestOrder(orderId);
  const { keyId, keySecret } = secrets();
  const client = new Razorpay({ key_id: keyId, key_secret: keySecret });
  try { return await client.orders.fetch(orderId) as unknown as RazorpayOrder; }
  catch { return null; }
}
