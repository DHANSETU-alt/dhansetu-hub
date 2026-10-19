import { redirect } from "next/navigation";
import { createServerSupabase, hasSupabasePublicConfig } from "@/lib/supabase/server";
import { CheckoutButton } from "@/components/checkout/CheckoutButton";
import { isTierId, TIERS } from "@/lib/payment/tiers";

export const dynamic = "force-dynamic";
export default async function CheckoutPage({ searchParams }: { searchParams: Promise<{ tier?: string }> }) {
  const params = await searchParams;
  const tier = isTierId(params.tier) ? params.tier : "smartbudget_pro";
  if (!hasSupabasePublicConfig()) redirect(`/login?next=${encodeURIComponent(`/checkout?tier=${tier}`)}&error=auth_unavailable`);
  const supabase = await createServerSupabase();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect(`/login?next=${encodeURIComponent(`/checkout?tier=${tier}`)}`);
  const item = TIERS[tier];
  return <main className="min-h-screen bg-slate-50 px-4 py-16"><section className="mx-auto max-w-xl space-y-6 rounded-2xl bg-white p-8 shadow-sm"><p className="font-semibold text-emerald-700">Signed in as {data.user.email}</p><h1 className="text-3xl font-bold">{item.label}</h1><p className="text-4xl font-black">₹{item.amountPaise / 100}<span className="text-base font-normal text-slate-500"> once</span></p><p>Lifetime access is activated automatically on this signed-in account after server verification.</p><CheckoutButton tier={tier} email={data.user.email ?? ""} /></section></main>;
}
