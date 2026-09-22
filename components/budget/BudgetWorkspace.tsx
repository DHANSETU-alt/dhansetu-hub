"use client";

import { useEffect, useMemo, useState } from "react";
import { LeakShield, type Transaction } from "./LeakShield";
import { StatementImporter } from "./StatementImporter";

type Direction = "income" | "expense";
type BudgetTransaction = Transaction & { direction: Direction; category: string; source: "manual" | "csv" };
type BudgetState = { income: number; cadence: "monthly" | "fortnightly" | "weekly" | "irregular"; householdSize: number; fixed: number; variableBudget: number; savings: number; transactions: BudgetTransaction[] };

const STORAGE_KEY = "dhansetu.smartbudget.v2";
const initial: BudgetState = { income: 0, cadence: "monthly", householdSize: 1, fixed: 0, variableBudget: 0, savings: 0, transactions: [] };
const money = (value: number) => `₹${Math.max(0, value).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
function fingerprint(transaction: Pick<BudgetTransaction, "date" | "merchant" | "amount" | "direction">) { return `${transaction.date.slice(0, 10)}|${transaction.merchant.trim().toLowerCase()}|${transaction.amount}|${transaction.direction}`; }

export function BudgetWorkspace() {
  const [state, setState] = useState<BudgetState>(initial);
  const [hydrated, setHydrated] = useState(false);
  const [syncStatus, setSyncStatus] = useState<"checking" | "synced" | "local">("checking");
  const [merchant, setMerchant] = useState("");
  const [amount, setAmount] = useState("");
  const [direction, setDirection] = useState<Direction>("expense");
  const [category, setCategory] = useState("Everyday");
  const [editingId, setEditingId] = useState<string | null>(null);

  useEffect(() => {
    const load = window.setTimeout(() => {
      try {
        const saved = window.localStorage.getItem(STORAGE_KEY);
        if (saved) { const parsed = JSON.parse(saved) as Partial<BudgetState>; setState({ ...initial, ...parsed, transactions: parsed.transactions ?? [] }); }
      } catch { /* Keep the workspace empty if storage is unavailable or corrupted. */ }
      setHydrated(true);
    }, 0);
    return () => window.clearTimeout(load);
  }, []);
  useEffect(() => {
    if (!hydrated) return;
    let active = true;
    void fetch("/api/smartbudget", { cache: "no-store" }).then(async (response) => {
      if (!active) return;
      if (!response.ok) { setSyncStatus("local"); return; }
      const remote = await response.json() as { profile: Partial<BudgetState> | null; transactions: BudgetTransaction[] };
      if (remote.profile || remote.transactions.length > 0) {
        setState((current) => ({ ...current, ...remote.profile, transactions: remote.transactions }));
      }
      setSyncStatus("synced");
    }).catch(() => { if (active) setSyncStatus("local"); });
    return () => { active = false; };
  }, [hydrated]);
  useEffect(() => { if (hydrated) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }, [hydrated, state]);
  useEffect(() => {
    if (!hydrated || syncStatus !== "synced") return;
    const timer = window.setTimeout(() => {
      void fetch("/api/smartbudget", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ profile: { income: state.income, cadence: state.cadence, householdSize: state.householdSize, fixed: state.fixed, variableBudget: state.variableBudget, savings: state.savings }, transactions: state.transactions }) }).then((response) => {
        if (response.status === 401 || response.status === 503) setSyncStatus("local");
      }).catch(() => setSyncStatus("local"));
    }, 700);
    return () => window.clearTimeout(timer);
  }, [hydrated, state, syncStatus]);

  const expenses = useMemo(() => state.transactions.filter((item) => item.direction === "expense").reduce((sum, item) => sum + item.amount, 0), [state.transactions]);
  const incomeTransactions = useMemo(() => state.transactions.filter((item) => item.direction === "income").reduce((sum, item) => sum + item.amount, 0), [state.transactions]);
  const totalIncome = state.income + incomeTransactions;
  const safeToSpend = totalIncome - state.fixed - state.savings - expenses;
  const leakTransactions = state.transactions.filter((item) => item.direction === "expense");

  function importTransactions(imported: Transaction[]) {
    setState((current) => { const existing = new Set(current.transactions.map(fingerprint)); const additions = imported.map((item) => ({ ...item, direction: "expense" as const, category: "Imported", source: "csv" as const })).filter((item) => !existing.has(fingerprint(item))); return { ...current, transactions: [...current.transactions, ...additions] }; });
  }
  function saveTransaction(event: React.FormEvent) {
    event.preventDefault(); const value = Number(amount); if (!merchant.trim() || !Number.isFinite(value) || value <= 0) return;
    const item: BudgetTransaction = { id: editingId ?? crypto.randomUUID(), merchant: merchant.trim(), amount: value, date: new Date().toISOString(), direction, category, source: "manual" };
    setState((current) => { const withoutEdited = current.transactions.filter((entry) => entry.id !== editingId); const duplicate = withoutEdited.some((entry) => fingerprint(entry) === fingerprint(item)); return duplicate ? current : { ...current, transactions: [...withoutEdited, item] }; });
    setMerchant(""); setAmount(""); setDirection("expense"); setCategory("Everyday"); setEditingId(null);
  }
  function editTransaction(item: BudgetTransaction) { setEditingId(item.id); setMerchant(item.merchant); setAmount(String(item.amount)); setDirection(item.direction); setCategory(item.category); }
  async function deleteTransaction(id: string) {
    if (syncStatus === "synced") {
      const response = await fetch(`/api/smartbudget/transactions/${id}`, { method: "DELETE" });
      if (!response.ok) setSyncStatus("local");
    }
    setState((current) => ({ ...current, transactions: current.transactions.filter((item) => item.id !== id) }));
    if (editingId === id) { setEditingId(null); setMerchant(""); setAmount(""); }
  }
  function exportData() { const rows = ["date,merchant,amount,direction,category,source", ...state.transactions.map((item) => [item.date.slice(0, 10), item.merchant, item.amount, item.direction, item.category, item.source].map((cell) => JSON.stringify(cell)).join(","))]; const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([rows.join("\n")], { type: "text/csv" })); link.download = "dhansetu-smartbudget.csv"; link.click(); URL.revokeObjectURL(link.href); }

  return <div className="space-y-6">
    <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><article className="rounded-2xl bg-slate-950 p-5 text-white"><p className="text-xs text-slate-400">Income received + planned</p><strong className="mt-2 block text-2xl text-emerald-300">{money(totalIncome)}</strong></article><article className="rounded-2xl border bg-white p-5"><p className="text-xs text-slate-500">Committed costs</p><strong className="mt-2 block text-2xl text-slate-950">{money(state.fixed)}</strong></article><article className="rounded-2xl border bg-white p-5"><p className="text-xs text-slate-500">Savings target</p><strong className="mt-2 block text-2xl text-slate-950">{money(state.savings)}</strong></article><article className={`rounded-2xl p-5 ${safeToSpend >= 0 ? "bg-emerald-100" : "bg-rose-100"}`}><p className="text-xs text-slate-600">Safe to spend</p><strong className="mt-2 block text-2xl text-slate-950">{safeToSpend < 0 ? "−" : ""}{money(Math.abs(safeToSpend))}</strong></article></section>
    <section className="grid gap-6 lg:grid-cols-[1fr_1fr]"><form className="space-y-4 rounded-2xl border bg-white p-5" onSubmit={(event) => event.preventDefault()}><div><h2 className="text-xl font-semibold text-slate-950">Your money setup</h2><p className="mt-1 text-sm text-slate-500">These assumptions stay on this device until account sync is enabled.</p></div><div className="grid gap-3 sm:grid-cols-2"><label className="block text-sm font-medium">Income cadence<select className="mt-1 w-full rounded-xl border p-3" value={state.cadence} onChange={(event) => setState({ ...state, cadence: event.target.value as BudgetState["cadence"] })}><option value="monthly">Monthly</option><option value="fortnightly">Fortnightly</option><option value="weekly">Weekly</option><option value="irregular">Irregular</option></select></label><label className="block text-sm font-medium">Household size<input className="mt-1 w-full rounded-xl border p-3" inputMode="numeric" min="1" type="number" value={state.householdSize} onChange={(event) => setState({ ...state, householdSize: Math.max(1, Number(event.target.value) || 1) })} /></label></div><label className="block text-sm font-medium">Planned income for this period (₹)<input className="mt-1 w-full rounded-xl border p-3" inputMode="numeric" value={state.income || ""} onChange={(event) => setState({ ...state, income: Number(event.target.value.replace(/[^0-9]/g, "")) || 0 })} placeholder="e.g. 75000" /></label><label className="block text-sm font-medium">Fixed obligations (₹)<input className="mt-1 w-full rounded-xl border p-3" inputMode="numeric" value={state.fixed || ""} onChange={(event) => setState({ ...state, fixed: Number(event.target.value.replace(/[^0-9]/g, "")) || 0 })} placeholder="Rent, EMIs, bills" /></label><label className="block text-sm font-medium">Variable budget (₹)<input className="mt-1 w-full rounded-xl border p-3" inputMode="numeric" value={state.variableBudget || ""} onChange={(event) => setState({ ...state, variableBudget: Number(event.target.value.replace(/[^0-9]/g, "")) || 0 })} placeholder="Food, travel, everyday" /></label><label className="block text-sm font-medium">Savings target (₹)<input className="mt-1 w-full rounded-xl border p-3" inputMode="numeric" value={state.savings || ""} onChange={(event) => setState({ ...state, savings: Number(event.target.value.replace(/[^0-9]/g, "")) || 0 })} placeholder="What you want to keep" /></label></form>
      <form className="space-y-4 rounded-2xl border bg-white p-5" onSubmit={saveTransaction}><div><h2 className="text-xl font-semibold text-slate-950">{editingId ? "Edit transaction" : "Add a transaction"}</h2><p className="mt-1 text-sm text-slate-500">Duplicate date, merchant, amount, and direction combinations are ignored.</p></div><div className="grid grid-cols-2 gap-3"><select className="w-full rounded-xl border p-3" value={direction} onChange={(event) => setDirection(event.target.value as Direction)}><option value="expense">Expense</option><option value="income">Income received</option></select><select className="w-full rounded-xl border p-3" value={category} onChange={(event) => setCategory(event.target.value)}><option>Everyday</option><option>Salary</option><option>Food</option><option>Transport</option><option>Subscriptions</option><option>Fees</option><option>Other</option></select></div><input className="w-full rounded-xl border p-3" required value={merchant} onChange={(event) => setMerchant(event.target.value)} placeholder="Merchant, employer, or description" /><input className="w-full rounded-xl border p-3" required inputMode="decimal" value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="Amount ₹" /><div className="flex gap-3"><button className="flex-1 rounded-xl bg-slate-950 p-3 font-semibold text-white" type="submit">{editingId ? "Save changes" : "Save locally"}</button>{editingId && <button className="rounded-xl border px-4" type="button" onClick={() => { setEditingId(null); setMerchant(""); setAmount(""); }}>Cancel</button>}</div></form></section>
    <StatementImporter onImport={importTransactions} />
    <section className="rounded-2xl border bg-white p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-semibold text-slate-950">Transactions and provenance</h2><p className="mt-1 text-sm text-slate-500">{state.transactions.length} records · local-only until sync is enabled.</p></div><button className="rounded-lg border px-3 py-2 text-sm" onClick={exportData} type="button">Export CSV</button></div>{state.transactions.length ? <div className="mt-5 divide-y">{state.transactions.slice().reverse().map((item) => <div className="flex flex-wrap items-center justify-between gap-3 py-3" key={item.id}><div><p className="font-medium text-slate-900">{item.merchant}</p><p className="text-xs text-slate-500">{item.date.slice(0, 10)} · {item.category} · source: {item.source}</p></div><div className="flex items-center gap-3"><strong className={item.direction === "income" ? "text-emerald-700" : "text-slate-900"}>{item.direction === "income" ? "+" : "−"}{money(item.amount)}</strong><button className="text-xs underline" type="button" onClick={() => editTransaction(item)}>Edit</button><button className="text-xs text-rose-700 underline" type="button" onClick={() => deleteTransaction(item.id)}>Delete</button></div></div>)}</div> : <p className="mt-5 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">Add income or expense records, or import a CSV/TSV statement to see real leak checks. No sample figures are shown.</p>}</section>
    <section className="rounded-2xl border bg-white p-5"><div><h2 className="text-xl font-semibold text-slate-950">Money LeakShield</h2><p className="mt-1 text-sm text-slate-500">Explainable flags from {leakTransactions.length} expense records. No AI claim.</p></div>{leakTransactions.length ? <div className="mt-5"><LeakShield transactions={leakTransactions} inflationRate={0} /></div> : <p className="mt-5 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">LeakShield activates when expense records are available.</p>}</section>
  </div>;
}
