import type { RazorpayOrder } from "./types";

type ProviderPayment = { id: string; order_id?: string | null; status: string; amount: number | string; currency: string; amount_refunded?: number };

export function capturedPaymentId(order: RazorpayOrder, payments: ProviderPayment[]) {
  const payment = payments.find((item) => item.status === "captured" && item.order_id === order.id && Number(item.amount) === order.amount && item.currency === order.currency && (item.amount_refunded ?? 0) === 0);
  return payment?.id ?? null;
}
