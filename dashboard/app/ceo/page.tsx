import { getDecisions, getCeoHealth, getGovernorStatus } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

const STATUS_TONE = { approved: "good", rejected: "bad", revise: "warn" } as const;
const HEALTH_TONE = { healthy: "good", degraded: "warn", down: "bad", unknown: "neutral" } as const;
const GOV_TONE = { operational: "good", degraded: "bad" } as const;

export default async function CeoDashboardPage() {
  const [{ decisions }, health, governor] = await Promise.all([getDecisions(30), getCeoHealth(), getGovernorStatus()]);

  const approved = decisions.filter((d) => d.status === "approved").length;
  const rejected = decisions.filter((d) => d.status === "rejected").length;
  const revise = decisions.filter((d) => d.status === "revise").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">CEO Dashboard</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Decisions score priority/risk/business-impact 1-10 and fail closed to &quot;revise&quot; if unparseable — never a silent approval.
          </p>
        </div>
        <AutoRefresh intervalSeconds={20} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatTile label="Approved" value={String(approved)} tone="good" />
        <StatTile label="Revise (needs founder input)" value={String(revise)} tone="warn" />
        <StatTile label="Rejected" value={String(rejected)} tone="bad" />
      </div>

      <Card>
        <CardHeader title="CEO Health Monitor" subtitle={`${health.total_tracked} recent CEO task(s) tracked`} />
        <CardBody>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatTile label="Status" value={health.status} tone={HEALTH_TONE[health.status]} />
            <StatTile label="Failure Count" value={String(health.failure_count)} tone={health.failure_count ? "warn" : "good"} />
            <StatTile label="Degraded (local fallback)" value={String(health.degraded_count)} tone={health.degraded_count ? "warn" : "good"} />
            <StatTile label="Recovery Attempts" value={String(health.recovery_attempts)} />
          </div>
          {health.last_error && (
            <div className="mt-4 text-xs text-[var(--muted-foreground)]">
              <span className="font-medium text-[var(--foreground)]">Last error</span> (task #{health.last_error.task_id}, {health.last_error.at}): {health.last_error.goal} — {health.last_error.result}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Governor" subtitle="Composite check: does every subsystem run with zero CEO dependency, right now?" />
        <CardBody>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
            <StatTile label="Governor Status" value={governor.status} tone={GOV_TONE[governor.status]} />
            <StatTile label="Failover Events (24h)" value={String(governor.failover_event_count_24h)} tone={governor.failover_event_count_24h ? "warn" : "good"} />
            <StatTile label="Subsystems Checked" value={String(Object.keys(governor.subsystems).length)} />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(governor.subsystems).map(([name, s]) => (
              <div key={name} className="flex items-center justify-between text-xs rounded-lg border border-[var(--border)] px-3 py-2">
                <span className="capitalize">{name.replace("_", " ")}</span>
                <Badge tone={s.ok ? "good" : "bad"}>{s.ok ? "OK" : "DOWN"}</Badge>
              </div>
            ))}
          </div>
          {governor.failover_events_24h.length > 0 && (
            <div className="mt-4 space-y-1.5">
              {governor.failover_events_24h.map((e) => (
                <div key={e.task_id} className="text-xs text-[var(--muted-foreground)]">
                  #{e.task_id} [{e.status}] {e.goal} — {e.at}
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="CEO Decisions" subtitle="Most recent 30" />
        <CardBody className="p-0">
          {decisions.length === 0 ? (
            <EmptyState>
              No decisions yet. Run <code>python3 -m orchestrator.cli --decide &quot;your goal&quot; --business 1</code>
            </EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {decisions.map((d) => (
                <div key={d.id} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium">{d.goal}</span>
                    <Badge tone={STATUS_TONE[d.status as keyof typeof STATUS_TONE] ?? "neutral"}>{d.status}</Badge>
                  </div>
                  <div className="mt-1.5 flex items-center gap-4 text-xs text-[var(--muted-foreground)]">
                    <span>priority {d.priority_score ?? "—"}</span>
                    <span>risk {d.risk_score ?? "—"}</span>
                    <span>impact {d.business_impact_score ?? "—"}</span>
                    <span className="font-mono-num">{d.created_at}</span>
                  </div>
                  {d.reason && <p className="mt-1.5 text-xs text-[var(--muted-foreground)] max-w-[70ch]">{d.reason}</p>}
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
