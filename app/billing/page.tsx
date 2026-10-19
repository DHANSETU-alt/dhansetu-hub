import { redirect } from "next/navigation";
import { createServerSupabase, hasSupabasePublicConfig } from "@/lib/supabase/server";
import { LogoutButton } from "@/components/auth/LogoutButton";

export const dynamic = "force-dynamic";
export default async function BillingPage() {
  if (!hasSupabasePublicConfig()) redirect("/login?next=/billing&error=auth_unavailable");
  const supabase = await createServerSupabase();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect("/login?next=/billing");
  const { data: purchases, error: purchasesError } = await supabase.from("purchases").select("id,tier,razorpay_order_id,razorpay_payment_id,amount_paise,currency,status,created_at,paid_at").eq("user_id", data.user.id).order("created_at", { ascending: false });
  return <main className="mx-auto min-h-screen max-w-4xl px-6 py-16"><div className="flex items-start justify-between gap-4"><div><h1 className="text-3xl font-bold">Billing</h1><p className="mt-2 text-slate-600">Purchases for {data.user.email}</p></div><LogoutButton /></div>{purchasesError && <p className="mt-8 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">Billing records are temporarily unavailable while the account database is being configured.</p>}<div className="mt-8 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b"><th className="p-3">Tier</th><th className="p-3">Order</th><th className="p-3">Amount</th><th className="p-3">Status</th><th className="p-3">Date</th></tr></thead><tbody>{(purchases ?? []).map((purchase) => <tr className="border-b" key={purchase.id}><td className="p-3">{purchase.tier}</td><td className="p-3 font-mono text-xs">{purchase.razorpay_order_id}</td><td className="p-3">₹{(purchase.amount_paise / 100).toFixed(2)}</td><td className="p-3">{purchase.status}</td><td className="p-3">{new Date(purchase.paid_at ?? purchase.created_at).toLocaleDateString("en-IN")}</td></tr>)}</tbody></table>{!purchases?.length && !purchasesError && <p className="py-8 text-slate-500">No purchases yet.</p>}</div></main>;
}
