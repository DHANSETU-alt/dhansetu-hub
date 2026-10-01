import { getCosts } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

export default async function CostLedgerPage() {
  const { cost_summary, recent_tool_calls } = await getCosts();
  const totalCost = cost_summary.reduce((sum, r) => sum + r.cost_usd, 0);
  const totalCalls = cost_summary.reduce((sum, r) => sum + r.calls, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Cost Ledger</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">Every model call is logged, local calls included, at $0.</p>
        </div>
        <AutoRefresh intervalSeconds={5} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatTile label="Total Calls" value={String(totalCalls)} />
        <StatTile label="Total API Cost" value={`$${totalCost.toFixed(4)}`} />
        <StatTile label="Providers Active" value={String(cost_summary.length)} />
      </div>

      <Card>
        <CardHeader title="By Provider" />
        <CardBody className="p-0">
          {cost_summary.length === 0 ? (
            <EmptyState>No calls logged yet.</EmptyState>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--muted-foreground)] border-b border-[var(--border)]">
                  <th className="px-5 py-2 font-medium">Provider</th>
                  <th className="px-5 py-2 font-medium">Calls</th>
                  <th className="px-5 py-2 font-medium">Tokens In</th>
                  <th className="px-5 py-2 font-medium">Tokens Out</th>
                  <th className="px-5 py-2 font-medium">Cost</th>
                </tr>
              </thead>
              <tbody>
                {cost_summary.map((r) => (
                  <tr key={r.provider} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-5 py-2">
                      <Badge tone={r.provider === "ollama" ? "local" : "cloud"}>{r.provider}</Badge>
                    </td>
                    <td className="px-5 py-2 font-mono-num">{r.calls}</td>
                    <td className="px-5 py-2 font-mono-num">{r.tokens_in}</td>
                    <td className="px-5 py-2 font-mono-num">{r.tokens_out}</td>
                    <td className="px-5 py-2 font-mono-num">${r.cost_usd.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Recent Tool Calls" subtitle="Full audit trail — allowed and denied" />
        <CardBody className="p-0">
          {recent_tool_calls.length === 0 ? (
            <EmptyState>No tool calls yet.</EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)] max-h-[480px] overflow-y-auto">
              {recent_tool_calls.map((c) => (
                <div key={c.id} className="px-5 py-2 text-sm flex items-center justify-between gap-3">
                  <span className="truncate">
                    #{c.task_id} {c.agent_id} → {c.tool_name}
                  </span>
                  <div className="flex items-center gap-2 shrink-0">
                    {c.duration_ms !== null && <span className="text-xs text-[var(--muted-foreground)] font-mono-num">{c.duration_ms}ms</span>}
                    <Badge tone={c.decision === "allowed" ? "good" : c.decision === "denied" ? "bad" : "neutral"}>{c.decision}</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
