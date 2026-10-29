import { createAdminSupabase } from "@/lib/supabase/admin";

export type FounderDashboardData = {
  gross: number;
  cost: number;
  commission: number;
  net: number;
  paidOrders: number;
  customers: number;
  transactionCount: number;
  warnings: string[];
};

export async function readFounderData(): Promise<FounderDashboardData> {
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
    return {
      gross: 0,
      cost: 0,
      commission: 0,
      net: 0,
      paidOrders: 0,
      customers: 0,
      transactionCount: 0,
      warnings: ["Founder data is unavailable until Supabase server configuration is present"],
    };
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
  const commission = (commissions.data ?? [])
    .filter((row) => row.event_type !== "paid")
    .reduce((sum, row) => sum + Number(row.amount_paise ?? 0), 0);

  return {
    gross,
    cost,
    commission,
    net: gross - cost - commission,
    paidOrders: paid.length,
    customers: (customers.data ?? []).length,
    transactionCount: activity.count ?? 0,
    warnings: [purchases.error, expenses.error, commissions.error, customers.error, activity.error]
      .filter(Boolean)
      .map((error) => error?.message ?? "Unknown data source error"),
  };
}
