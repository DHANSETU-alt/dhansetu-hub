import { getDecisions } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

const STATUS_TONE = { approved: "good", rejected: "bad", revise: "warn" } as const;

export default async function CeoDashboardPage() {
  const { decisions } = await getDecisions(30);

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
