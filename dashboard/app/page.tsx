import { getOverview } from "@/lib/api";
import { Card, CardHeader, CardBody, StatTile, Badge, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

export default async function ExecutiveDashboard() {
  const overview = await getOverview().catch(() => null);

  if (!overview) {
    return (
      <Card>
        <CardHeader title="API unreachable" />
        <CardBody>
          <p className="text-sm text-[var(--muted-foreground)]">
            Could not reach the Shakthi API. Start it with{" "}
            <code className="text-[var(--ink)]">python3 -m orchestrator.api</code> in the shakthi-os directory, then reload.
          </p>
        </CardBody>
      </Card>
    );
  }

  const ollama = overview.cost_summary.find((c) => c.provider === "ollama");
  const claude = overview.cost_summary.find((c) => c.provider === "claude");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Executive Dashboard</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">Founder-level overview across every business and agent.</p>
        </div>
        <AutoRefresh intervalSeconds={15} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Businesses" value={String(overview.businesses.length)} />
        <StatTile label="Registered Agents" value={String(overview.agent_count)} />
        <StatTile label="Active Tasks" value={String(overview.active_tasks)} tone={overview.active_tasks > 0 ? "warn" : "good"} />
        <StatTile
          label="Local vs Cloud Calls"
          value={`${ollama?.calls ?? 0} / ${claude?.calls ?? 0}`}
          hint="ollama / claude"
        />
      </div>

      <Card>
        <CardHeader title="Recent Tasks" subtitle="Most recent 15 tasks across all businesses" />
        <CardBody className="p-0">
          {overview.recent_tasks.length === 0 ? (
            <EmptyState>No tasks yet. Run one from the CLI to see it here.</EmptyState>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--muted-foreground)] border-b border-[var(--border)]">
                  <th className="px-5 py-2 font-medium">ID</th>
                  <th className="px-5 py-2 font-medium">Agent</th>
                  <th className="px-5 py-2 font-medium">Business</th>
                  <th className="px-5 py-2 font-medium">Status</th>
                  <th className="px-5 py-2 font-medium">Risk</th>
                  <th className="px-5 py-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {overview.recent_tasks.map((t) => (
                  <tr key={t.id} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-5 py-2 font-mono-num text-[var(--muted-foreground)]">#{t.id}</td>
                    <td className="px-5 py-2">{t.agent_id}</td>
                    <td className="px-5 py-2 text-[var(--muted-foreground)]">{t.business_id ?? "—"}</td>
                    <td className="px-5 py-2">
                      <Badge tone={t.status === "done" ? "good" : t.status === "failed" ? "bad" : "warn"}>{t.status}</Badge>
                    </td>
                    <td className="px-5 py-2">
                      <Badge tone={t.risk_level === "critical" ? "bad" : "neutral"}>{t.risk_level}</Badge>
                    </td>
                    <td className="px-5 py-2 text-[var(--muted-foreground)] font-mono-num">{t.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Businesses" />
        <CardBody className="flex flex-wrap gap-2">
          {overview.businesses.map((b) => (
            <span key={b.id} className="text-sm rounded-md border border-[var(--border)] px-3 py-1">
              #{b.id} {b.name}
            </span>
          ))}
        </CardBody>
      </Card>
    </div>
  );
}
