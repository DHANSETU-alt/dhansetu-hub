import { redirect } from "next/navigation";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { requireFounder } from "@/lib/auth/founder";

export const dynamic = "force-dynamic";

function money(paise: number) { return `₹${(paise / 100).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`; }

async function readFounderData() {
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
    return { gross: 0, cost: 0, commission: 0, net: 0, paidOrders: 0, customers: 0, transactionCount: 0, warnings: ["Founder data is unavailable until Supabase server configuration is present"] };
  }
  const admin = createAdminSupabase();
  const [purchases, expenses, commissions, customers, activity] = await Promise.all([
    admin.from("purchases").select("amount_paise,status,razorpay_payment_id,created_at,paid_at").eq("status", "paid").order("paid_at", { ascending: false }).limit(500),
    admin.from("founder_expenses").select("amount_paise,status").neq("status", "void").limit(500),
    admin.from("commission_events").select("amount_paise,event_type").in("event_type", ["eligible", "hold", "approved", "paid"]).limit(500),
    admin.from("profiles").select("id,plan").limit(1000),
    admin.from("money_transactions").select("id", { count: "exact", head: true }),
  ]);
  const paid = purchases.data ?? [];
  const gross = paid.reduce((sum, row) => sum + Number(row.amount_paise ?? 0), 0);
  const cost = (expenses.data ?? []).reduce((sum, row) => sum + Number(row.amount_paise ?? 0), 0);
  const commission = (commissions.data ?? []).filter((row) => row.event_type !== "paid").reduce((sum, row) => sum + Number(row.amount_paise ?? 0), 0);
  return { gross, cost, commission, net: gross - cost - commission, paidOrders: paid.length, customers: (customers.data ?? []).length, transactionCount: activity.count ?? 0, warnings: [purchases.error, expenses.error, commissions.error, customers.error, activity.error].filter(Boolean).map((error) => error?.message ?? "Unknown data source error") };
}

export default async function FounderDashboard() {
  const access = await requireFounder();
  if (!access.user) redirect("/login?next=/founder");
  if (!access.allowed) return <main className="mx-auto min-h-screen max-w-xl px-6 py-20"><h1 className="text-3xl font-bold">Founder access required</h1><p className="mt-3 text-slate-600">This account is authenticated but is not in the server-side founder allowlist.</p></main>;
  const data = await readFounderData();
  const configured = ["NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET"].every((name) => Boolean(process.env[name]));
  return <main className="min-h-screen bg-slate-950 px-5 py-10 text-white"><div className="mx-auto max-w-7xl"><header className="flex flex-wrap items-end justify-between gap-5"><div><p className="text-xs font-bold uppercase tracking-[.2em] text-emerald-300">DhanSetu · private command center</p><h1 className="mt-3 text-4xl font-black tracking-tight">Revenue reality</h1><p className="mt-2 text-slate-400">Server-derived figures only · {access.user.email}</p></div><span className={`rounded-full border px-3 py-2 text-xs ${configured ? "border-emerald-400/40 text-emerald-300" : "border-amber-400/40 text-amber-300"}`}>{configured ? "Payment configuration present" : "Payment configuration incomplete"}</span></header><section className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{[["Gross paid", money(data.gross)], ["Net after recorded costs", money(data.net)], ["Paid orders", String(data.paidOrders)], ["Customers in profiles", String(data.customers)]].map(([label, value]) => <article className="rounded-2xl border border-white/10 bg-white/5 p-5" key={label}><p className="text-sm text-slate-400">{label}</p><strong className="mt-3 block text-3xl text-emerald-300">{value}</strong></article>)}</section><section className="mt-6 grid gap-4 lg:grid-cols-3"><article className="rounded-2xl border border-white/10 bg-white/5 p-5"><h2 className="font-bold">Recorded costs</h2><p className="mt-3 text-2xl">{money(data.cost)}</p><p className="mt-2 text-xs text-slate-500">Actual entries only; no estimated expenses.</p></article><article className="rounded-2xl border border-white/10 bg-white/5 p-5"><h2 className="font-bold">Commission accrued</h2><p className="mt-3 text-2xl">{money(data.commission)}</p><p className="mt-2 text-xs text-slate-500">Pending and eligible events, excluding paid payouts.</p></article><article className="rounded-2xl border border-white/10 bg-white/5 p-5"><h2 className="font-bold">Money activity rows</h2><p className="mt-3 text-2xl">{data.transactionCount}</p><p className="mt-2 text-xs text-slate-500">Customer-owned transaction records.</p></article></section>{data.warnings.length > 0 && <section className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 text-sm text-amber-100"><b>Data sources requiring migration or review</b><ul className="mt-2 list-disc pl-5">{data.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></section>}<p className="mt-8 text-xs text-slate-500">This dashboard never displays demo revenue. Empty or unavailable tables remain visible as a data-source warning.</p></div></main>;
}
