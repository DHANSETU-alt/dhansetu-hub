import type { SupabaseClient } from "@supabase/supabase-js";

/** First-party cookie holding the referral code that introduced this visitor. */
export const REFERRAL_COOKIE = "ds_ref";

/** First touch wins: a later link does not overwrite the partner who actually introduced the visitor. */
export const REFERRAL_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

const CODE_PATTERN = /^[A-Za-z0-9_-]{4,32}$/;

/**
 * Codes arrive from an untrusted query string and are later used in a database lookup,
 * so anything not matching the issued shape is discarded rather than stored.
 */
export function normaliseReferralCode(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const trimmed = raw.trim();
  return CODE_PATTERN.test(trimmed) ? trimmed : null;
}

/** Resolves a code to the partner it belongs to. Returns null when the code is unknown. */
export async function partnerIdForCode(
  supabase: SupabaseClient,
  code: string,
): Promise<string | null> {
  const valid = normaliseReferralCode(code);
  if (!valid) return null;
  const { data, error } = await supabase
    .from("referral_links")
    .select("partner_id")
    .eq("code", valid)
    .maybeSingle();
  if (error || !data) return null;
  return (data as { partner_id: string }).partner_id;
}

export type EligibilityInput = {
  purchaseStatus: string;
  amountPaise: number;
  referralCode: string | null;
};

/**
 * Commission becomes eligible only on a purchase the payment provider has confirmed as paid.
 * A redirect, a client-supplied flag, or a pending order never qualifies.
 */
export function qualifiesForCommission(input: EligibilityInput): boolean {
  if (input.purchaseStatus !== "paid") return false;
  if (!Number.isInteger(input.amountPaise) || input.amountPaise <= 0) return false;
  return normaliseReferralCode(input.referralCode) !== null;
}

/**
 * Records one 'eligible' event for a settled purchase. Safe to call repeatedly: a purchase that
 * already has an eligible event is left alone, so webhook retries cannot credit a partner twice.
 */
export async function recordEligibleCommission(
  supabase: SupabaseClient,
  params: { purchaseId: string; partnerId: string },
): Promise<"recorded" | "already_recorded" | "failed"> {
  const existing = await supabase
    .from("commission_events")
    .select("id")
    .eq("purchase_id", params.purchaseId)
    .eq("event_type", "eligible")
    .maybeSingle();
  if (existing.error) return "failed";
  if (existing.data) return "already_recorded";

  const { error } = await supabase.from("commission_events").insert({
    partner_id: params.partnerId,
    purchase_id: params.purchaseId,
    event_type: "eligible",
  });
  return error ? "failed" : "recorded";
}
