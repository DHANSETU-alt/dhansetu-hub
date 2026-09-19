import { fetchOrder } from "./razorpay";
import { purchaseByOrder } from "./records";
import { isTierId, TIERS } from "./tiers";

export async function validatedPaidOrder(orderId: string) {
  const [order, purchase] = await Promise.all([fetchOrder(orderId), purchaseByOrder(orderId)]);
  if (!order || !purchase) throw new Error("Order not found");
  if (!isTierId(order.notes?.tier) || order.notes.tier !== purchase.tier) throw new Error("Order tier mismatch");
  if (order.notes?.user_id !== purchase.user_id) throw new Error("Order user mismatch");
  const tier = TIERS[purchase.tier];
  if (order.amount !== tier.amountPaise || purchase.amount_paise !== tier.amountPaise) throw new Error("Order amount mismatch");
  if (order.currency !== tier.currency || purchase.currency !== tier.currency) throw new Error("Order currency mismatch");
  return { order, purchase };
}
