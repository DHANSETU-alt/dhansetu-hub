import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { authenticatedUser } from "@/lib/payment/auth";
import { createServerSupabase } from "@/lib/supabase/server";

const applicationSchema = z.object({
  kind: z.enum(["affiliate", "tax_provider", "gst_provider", "career_provider", "insurance_partner"]),
  displayName: z.string().trim().min(2).max(120),
  contactEmail: z.string().trim().email().max(254),
  notes: z.string().trim().max(2_000).optional().default(""),
  disclosureAccepted: z.literal(true),
});

export async function POST(request: NextRequest) {
  const user = await authenticatedUser(request);
  if (!user) return NextResponse.json({ error: "Sign in before applying" }, { status: 401 });
  let body: unknown;
  try { body = await request.json(); } catch { return NextResponse.json({ error: "Invalid request" }, { status: 400 }); }
  const parsed = applicationSchema.safeParse(body);
  if (!parsed.success) return NextResponse.json({ error: "Complete the application and accept the disclosure" }, { status: 400 });
  const supabase = await createServerSupabase();
  const { error } = await supabase.from("partner_applications").insert({
    applicant_user_id: user.id, kind: parsed.data.kind, display_name: parsed.data.displayName,
    contact_email: parsed.data.contactEmail, notes: parsed.data.notes, disclosure_accepted_at: new Date().toISOString(),
  });
  if (error) return NextResponse.json({ error: "Applications are temporarily unavailable" }, { status: 503 });
  return NextResponse.json({ status: "pending_review" }, { status: 201 });
}
