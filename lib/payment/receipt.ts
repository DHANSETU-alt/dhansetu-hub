import { Resend } from "resend";
import { TIERS, type TierId } from "./tiers";

export async function sendReceipt(input: { email: string; orderId: string; paymentId: string; tier: TierId; paidAt: string }) {
  const key = process.env.RESEND_API_KEY;
  if (!key) {
    console.warn("[receipt] RESEND_API_KEY is not configured; receipt skipped", { orderId: input.orderId });
    return;
  }
  const tier = TIERS[input.tier];
  await new Resend(key).emails.send({
    from: process.env.RESEND_FROM_EMAIL ?? "receipts@dhansetuhub.in",
    to: input.email,
    subject: `DhanSetu Hub receipt — ${input.orderId}`,
    html: `<h1>Payment receipt</h1><p>Order: ${input.orderId}</p><p>Payment: ${input.paymentId}</p><p>Amount: ₹${(tier.amountPaise / 100).toFixed(2)}</p><p>Tier: ${tier.label}</p><p>Date: ${input.paidAt}</p><p><a href="${process.env.NEXT_PUBLIC_APP_URL ?? "https://budget.dhansetuhub.in"}">Open DhanSetu Hub</a></p>`,
  });
}
