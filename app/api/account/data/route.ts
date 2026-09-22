import { NextRequest, NextResponse } from "next/server";
import { authenticatedUser } from "@/lib/payment/auth";
import { createServerSupabase } from "@/lib/supabase/server";

export async function DELETE(request: NextRequest) {
  const user = await authenticatedUser(request);
  if (!user) return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  let body: unknown;
  try { body = await request.json(); } catch { return NextResponse.json({ error: "Explicit confirmation required" }, { status: 400 }); }
  if (!body || typeof body !== "object" || (body as { confirmation?: unknown }).confirmation !== "DELETE_MY_DATA") return NextResponse.json({ error: "Type DELETE_MY_DATA to confirm" }, { status: 400 });
  const supabase = await createServerSupabase();
  const { error } = await supabase.rpc("delete_my_workspace_data");
  if (error) return NextResponse.json({ error: "Personal data deletion is temporarily unavailable" }, { status: 503 });
  return NextResponse.json({ deleted: true, retained: ["verified payment and entitlement records required for billing, fraud prevention, and legal accounting"] });
}
