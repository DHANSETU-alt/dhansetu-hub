import type { TierId } from "./tiers";

export type Purchase = {
  id: string;
  user_id: string;
  tier: TierId;
  razorpay_order_id: string;
  razorpay_payment_id: string | null;
  amount_paise: number;
  currency: string;
  status: "created" | "paid" | "failed";
  consented_at: string;
  consent_ip: string;
  terms_version: string;
  created_at: string;
  paid_at: string | null;
};

export type RazorpayOrder = {
  id: string;
  amount: number;
  currency: string;
  status: string;
  notes: { user_id?: string; tier?: string };
};
