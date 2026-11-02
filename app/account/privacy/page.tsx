import { redirect } from "next/navigation";
import { DataControls } from "@/components/account/DataControls";
import { getCurrentAuthSession } from "@/lib/better-auth-session";

export const dynamic = "force-dynamic";

export default async function AccountPrivacyPage() {
  const session = await getCurrentAuthSession();
  if (!session?.user) redirect("/login?next=/account/privacy");
  return <main className="mx-auto min-h-screen max-w-2xl space-y-8 bg-slate-50 px-5 py-16"><header><p className="text-xs font-bold uppercase tracking-[.2em] text-emerald-700">DhanSetu · privacy controls</p><h1 className="mt-3 text-4xl font-black tracking-tight text-slate-950">Your data, your control</h1><p className="mt-3 text-slate-600">Signed in as {session.user.email}. Export local tax/GST workspaces before using deletion if you need a copy.</p></header><DataControls /></main>;
}
