import { getClientHealthOverview } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

export default async function ClientSuccessDashboardPage() {
  const { clients, total_clients, avg_health_score, at_risk_count } = await getClientHealthOverview();
  const atRisk = clients.filter((c) => c.health && c.health.score < 40);
  const scoreTone = (score: number) => (score >= 70 ? "good" : score >= 40 ? "warn" : "bad");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Client Success Dashboard</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            A client is a won lead. Health score is computed from product_usage and product_subscriptions —
            run <code>python3 -m orchestrator.cli --client-health-scan</code> to refresh.
          </p>
        </div>
        <AutoRefresh intervalSeconds={30} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Total Clients" value={String(total_clients)} />
        <StatTile
          label="Avg Health Score"
          value={avg_health_score === null ? "—" : `${avg_health_score}/100`}
          tone={avg_health_score === null ? "neutral" : (scoreTone(avg_health_score) as never)}
        />
        <StatTile label="At Risk" value={String(at_risk_count)} tone={at_risk_count > 0 ? "bad" : "good"} />
        <StatTile label="Retention Rate" value={total_clients === 0 ? "—" : `${Math.round(((total_clients - at_risk_count) / total_clients) * 100)}%`} />
      </div>

      <Card>
        <CardHeader title="At-Risk Clients" subtitle="Health score below 40/100" />
        <CardBody className="p-0">
          {atRisk.length === 0 ? (
            <EmptyState>No at-risk clients — or none scored yet. Run --client-health-scan.</EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {atRisk.map((c) => (
                <div key={c.id} className="px-5 py-2.5 flex items-center justify-between">
                  <span className="text-sm">{c.name} — {c.email}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-[var(--muted-foreground)]">
                      {c.health?.signals.days_since_last_use != null ? `${Math.round(Number(c.health.signals.days_since_last_use))}d since last use` : "no usage yet"}
                    </span>
                    <Badge tone={scoreTone(c.health!.score) as never}>{c.health!.score}/100</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="All Clients" subtitle={`${total_clients} won lead(s)`} />
        <CardBody className="p-0">
          {clients.length === 0 ? (
            <EmptyState>No won leads yet.</EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {clients.map((c) => (
                <div key={c.id} className="px-5 py-2.5 flex items-center justify-between">
                  <span className="text-sm">{c.name} — {c.email}</span>
                  {c.health ? (
                    <Badge tone={scoreTone(c.health.score) as never}>{c.health.score}/100</Badge>
                  ) : (
                    <span className="text-xs text-[var(--muted-foreground)]">not scored yet</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
