import { NextRequest, NextResponse } from "next/server";
import { authenticatedUser } from "@/lib/payment/auth";
import { createServerSupabase } from "@/lib/supabase/server";

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const user = await authenticatedUser(request);
  if (!user) return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(id)) return NextResponse.json({ error: "Invalid transaction id" }, { status: 400 });
  const supabase = await createServerSupabase();
  const { error } = await supabase.from("money_transactions").delete().eq("id", id).eq("user_id", user.id);
  if (error) return NextResponse.json({ error: "SmartBudget sync is unavailable until its reviewed database migration is applied" }, { status: 503 });
  return NextResponse.json({ deleted: true });
}
