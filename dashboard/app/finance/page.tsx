import { getFinanceAll, getFinanceReport } from "@/lib/api";
import { Card, CardHeader, CardBody, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

function fmt(n: number) {
  return `$${n.toFixed(2)}`;
}

export default async function FinanceDashboardPage() {
  const [monthly, allBusinesses] = await Promise.all([getFinanceReport("monthly"), getFinanceAll("monthly")]);

  const mrr = allBusinesses.reports.reduce((sum, r) => sum + r.report.revenue_usd, 0);
  const arr = mrr * 12;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Finance Dashboard</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Revenue/expense are whatever&apos;s logged via <code>--finance-entry</code> — no live billing integration exists.
          </p>
        </div>
        <AutoRefresh intervalSeconds={30} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Revenue (mo)" value={fmt(monthly.revenue_usd)} />
        <StatTile label="Expenses (mo)" value={fmt(monthly.expense_usd)} />
        <StatTile label="Profit (mo)" value={fmt(monthly.profit_usd)} tone={monthly.profit_usd >= 0 ? "good" : "bad"} />
        <StatTile label="AI Spend (mo)" value={`$${monthly.api_cost_usd.toFixed(4)}`} hint={`${monthly.ollama_calls} local calls`} />
        <StatTile label="MRR (approx.)" value={fmt(mrr)} hint="sum of businesses' monthly revenue entries" />
        <StatTile label="ARR (approx.)" value={fmt(arr)} hint="MRR × 12, not a real annualized model" />
        <StatTile
          label="Ollama Savings (mo)"
          value={`$${monthly.ollama_estimated_savings_usd.toFixed(4)}`}
          hint="vs. running local calls on Claude"
          tone="good"
        />
        <StatTile label="Cost by Provider" value={String(monthly.cost_by_provider.length)} hint="providers active this period" />
      </div>

      <Card>
        <CardHeader title="Profitability by Business" subtitle="Monthly" />
        <CardBody className="p-0">
          {allBusinesses.reports.every((r) => r.report.revenue_usd === 0 && r.report.expense_usd === 0) ? (
            <EmptyState>No finance entries logged yet for any business.</EmptyState>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--muted-foreground)] border-b border-[var(--border)]">
                  <th className="px-5 py-2 font-medium">Business</th>
                  <th className="px-5 py-2 font-medium">Revenue</th>
                  <th className="px-5 py-2 font-medium">Expense</th>
                  <th className="px-5 py-2 font-medium">Profit</th>
                </tr>
              </thead>
              <tbody>
                {allBusinesses.reports
                  .filter((r) => r.report.revenue_usd || r.report.expense_usd)
                  .map(({ business, report }) => (
                    <tr key={business.id} className="border-b border-[var(--border)] last:border-0">
                      <td className="px-5 py-2">{business.name}</td>
                      <td className="px-5 py-2 font-mono-num">{fmt(report.revenue_usd)}</td>
                      <td className="px-5 py-2 font-mono-num">{fmt(report.expense_usd)}</td>
                      <td className="px-5 py-2 font-mono-num" style={{ color: report.profit_usd >= 0 ? "var(--good)" : "var(--bad)" }}>
                        {fmt(report.profit_usd)}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
