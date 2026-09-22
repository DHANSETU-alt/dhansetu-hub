import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { authenticatedUser } from "@/lib/payment/auth";
import { createServerSupabase } from "@/lib/supabase/server";

const profileSchema = z.object({
  income: z.number().finite().min(0).max(1_000_000_000),
  cadence: z.enum(["monthly", "fortnightly", "weekly", "irregular"]),
  householdSize: z.number().int().min(1).max(100),
  fixed: z.number().finite().min(0).max(1_000_000_000),
  variableBudget: z.number().finite().min(0).max(1_000_000_000),
  savings: z.number().finite().min(0).max(1_000_000_000),
});

const transactionSchema = z.object({
  id: z.string().uuid(),
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}/),
  merchant: z.string().trim().min(1).max(240),
  amount: z.number().finite().positive().max(1_000_000_000),
  direction: z.enum(["income", "expense"]),
  category: z.string().trim().min(1).max(80),
  source: z.enum(["manual", "csv"]),
});

const payloadSchema = z.object({
  profile: profileSchema,
  transactions: z.array(transactionSchema).max(10_000),
});

export async function GET(request: NextRequest) {
  const user = await authenticatedUser(request);
  if (!user) return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  const supabase = await createServerSupabase();
  const [profileResult, transactionResult] = await Promise.all([
    supabase.from("budget_profiles").select("monthly_income_paise,cadence,household_size,fixed_obligations_paise,variable_budget_paise,savings_target_paise").eq("user_id", user.id).maybeSingle(),
    supabase.from("money_transactions").select("id,occurred_on,merchant,description,amount_paise,direction,category,source").eq("user_id", user.id).order("occurred_on", { ascending: false }).limit(10_000),
  ]);
  if (profileResult.error || transactionResult.error) return NextResponse.json({ error: "SmartBudget sync is unavailable until its reviewed database migration is applied" }, { status: 503 });
  return NextResponse.json({
    profile: profileResult.data ? {
      income: Number(profileResult.data.monthly_income_paise) / 100,
      cadence: profileResult.data.cadence,
      householdSize: profileResult.data.household_size,
      fixed: Number(profileResult.data.fixed_obligations_paise) / 100,
      variableBudget: Number(profileResult.data.variable_budget_paise) / 100,
      savings: Number(profileResult.data.savings_target_paise) / 100,
    } : null,
    transactions: (transactionResult.data ?? []).map((item) => ({
      id: item.id, date: item.occurred_on, merchant: item.merchant ?? item.description,
      amount: Number(item.amount_paise) / 100, direction: item.direction,
      category: item.category, source: item.source === "csv" ? "csv" : "manual",
    })),
  });
}

export async function POST(request: NextRequest) {
  const user = await authenticatedUser(request);
  if (!user) return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  let body: unknown;
  try { body = await request.json(); } catch { return NextResponse.json({ error: "Invalid request" }, { status: 400 }); }
  const parsed = payloadSchema.safeParse(body);
  if (!parsed.success) return NextResponse.json({ error: "Invalid SmartBudget data" }, { status: 400 });
  const supabase = await createServerSupabase();
  const { profile, transactions } = parsed.data;
  const profileResult = await supabase.from("budget_profiles").upsert({
    user_id: user.id, monthly_income_paise: Math.round(profile.income * 100), cadence: profile.cadence,
    household_size: profile.householdSize, fixed_obligations_paise: Math.round(profile.fixed * 100),
    variable_budget_paise: Math.round(profile.variableBudget * 100), savings_target_paise: Math.round(profile.savings * 100),
  }, { onConflict: "user_id" });
  if (profileResult.error) return NextResponse.json({ error: "SmartBudget sync is unavailable until its reviewed database migration is applied" }, { status: 503 });
  if (transactions.length > 0) {
    const transactionResult = await supabase.from("money_transactions").upsert(transactions.map((item) => ({
      id: item.id, user_id: user.id, occurred_on: item.date.slice(0, 10), description: item.merchant,
      merchant: item.merchant, category: item.category, amount_paise: Math.round(item.amount * 100),
      direction: item.direction, source: item.source, import_fingerprint: `${item.date.slice(0, 10)}|${item.merchant.trim().toLowerCase()}|${item.amount}|${item.direction}`,
    })), { onConflict: "id" });
    if (transactionResult.error) return NextResponse.json({ error: "Some transactions could not be synced" }, { status: 503 });
  }
  return NextResponse.json({ synced: true, transactionCount: transactions.length });
}
