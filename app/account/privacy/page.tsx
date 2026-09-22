import { redirect } from "next/navigation";
import { DataControls } from "@/components/account/DataControls";
import { createServerSupabase, hasSupabasePublicConfig } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export default async function AccountPrivacyPage() {
  if (!hasSupabasePublicConfig()) redirect("/login?next=/account/privacy&error=auth_unavailable");
  const supabase = await createServerSupabase();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect("/login?next=/account/privacy");
  return <main className="mx-auto min-h-screen max-w-2xl space-y-8 bg-slate-50 px-5 py-16"><header><p className="text-xs font-bold uppercase tracking-[.2em] text-emerald-700">DhanSetu · privacy controls</p><h1 className="mt-3 text-4xl font-black tracking-tight text-slate-950">Your data, your control</h1><p className="mt-3 text-slate-600">Signed in as {data.user.email}. Export local tax/GST workspaces before using deletion if you need a copy.</p></header><DataControls /></main>;
}
