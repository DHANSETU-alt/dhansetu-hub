import { getOverview, getGovernorStatus, getCeoHealth, getIncidents, getWorkers, getPaymentLinks, getSecurityLatest, getInitiatives } from "@/lib/api";
import { Card, CardHeader, CardBody, StatTile, Badge, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";
import Link from "next/link";

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

  const [governor, ceoHealth, incidentsResult, workersResult, paymentsResult, securityResult, initiativesResult] = await Promise.all([
    getGovernorStatus().catch(() => null),
    getCeoHealth().catch(() => null),
    getIncidents().catch(() => null),
    getWorkers(20).catch(() => null),
    getPaymentLinks(20).catch(() => null),
    getSecurityLatest().catch(() => null),
    getInitiatives("running").catch(() => null),
  ]);
  const runningInitiatives = initiativesResult?.initiatives ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Executive Dashboard</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">Founder-level overview across every business, agent, and system built this session.</p>
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
        <CardHeader title="System Status" subtitle="Live, across every subsystem — not just the original task ledger above" />
        <CardBody>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <Link href="/mission-control" className="block">
              <StatTile label="Governor" value={governor?.status ?? "—"} tone={governor?.status === "operational" ? "good" : governor ? "bad" : "neutral"} />
            </Link>
            <Link href="/ceo" className="block">
              <StatTile label="CEO Health" value={ceoHealth?.status ?? "—"} tone={ceoHealth?.status === "healthy" ? "good" : ceoHealth?.status === "degraded" ? "warn" : ceoHealth ? "bad" : "neutral"} />
            </Link>
            <Link href="/ert" className="block">
              <StatTile label="Open Incidents" value={incidentsResult ? String(incidentsResult.open_count) : "—"} tone={incidentsResult?.critical_count ? "bad" : incidentsResult?.open_count ? "warn" : "good"} />
            </Link>
            <Link href="/workers" className="block">
              <StatTile label="Worker Queue" value={workersResult ? String(workersResult.load_balancer.queue_depth) : "—"} tone={workersResult?.load_balancer.overflowing ? "bad" : "good"} />
            </Link>
            <Link href="/payments" className="block">
              <StatTile label="Payments Collected" value={paymentsResult ? `₹${paymentsResult.total_paid_inr.toLocaleString("en-IN")}` : "—"} tone="good" />
            </Link>
            <Link href="/security" className="block">
              <StatTile label="Security Score" value={securityResult?.latest_report ? `${securityResult.latest_report.score}/100` : "—"}
                         tone={securityResult?.latest_report ? (securityResult.latest_report.score >= 70 ? "good" : "bad") : "neutral"} />
            </Link>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Founder Tasks — running now"
          subtitle="Task 1, Task 2, ... — real % complete from real milestones"
          action={
            <Link href="/initiatives" className="text-xs font-mono text-[var(--local)] hover:underline">
              View all →
            </Link>
          }
        />
        <CardBody>
          {runningInitiatives.length === 0 ? (
            <EmptyState>No task currently running.</EmptyState>
          ) : (
            <div className="space-y-3">
              {runningInitiatives.map((init) => (
                <Link key={init.id} href="/initiatives" className="block">
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-[var(--ink)]">
                      Task {init.seq} — {init.title}
                    </span>
                    <span className="font-mono-num text-[var(--muted-foreground)]">
                      {init.percent_complete}% ({init.milestone_done}/{init.milestone_total})
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-[var(--surface-2)] overflow-hidden">
                    <div
                      className="h-full rounded-full bg-[var(--local)]"
                      style={{ width: `${init.percent_complete}%` }}
                    />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

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
