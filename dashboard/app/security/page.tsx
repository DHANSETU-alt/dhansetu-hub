import { getSecurityLatest } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

export default async function SecurityDashboardPage() {
  const { latest_report, recent_denied_calls } = await getSecurityLatest();
  const score = latest_report?.score ?? null;
  const scoreTone = score === null ? "neutral" : score >= 90 ? "good" : score >= 70 ? "warn" : "bad";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Security Dashboard</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Findings are deterministic checks (secret patterns, permission review, site heuristics) — not a local model&apos;s judgment.
          </p>
        </div>
        <AutoRefresh intervalSeconds={1} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Security Score" value={score === null ? "—" : `${score}/100`} tone={scoreTone as never} />
        <StatTile label="Open Findings" value={String(latest_report?.findings.length ?? 0)} />
        <StatTile label="Denied Tool Calls" value={String(recent_denied_calls.length)} hint="recent, all businesses" />
        <StatTile label="SSL / Website Health" value="N/A" hint="no live deployment yet — see Website Monitoring" />
      </div>

      <Card>
        <CardHeader title="Findings" subtitle={latest_report ? `Report #${latest_report.id} · ${latest_report.created_at}` : "No scan yet"} />
        <CardBody className="p-0">
          {!latest_report || latest_report.findings.length === 0 ? (
            <EmptyState>
              No findings. Run <code>python3 -m orchestrator.cli --security-review --business 1</code> to scan.
            </EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {latest_report.findings.map((f, i) => (
                <div key={i} className="px-5 py-2.5 flex items-center justify-between">
                  <span className="text-sm">{f.check}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-[var(--muted-foreground)]">{f.file ?? f.agent ?? ""}</span>
                    <Badge tone={f.type === "secret" ? "bad" : f.type === "site_risk" ? "warn" : "neutral"}>{f.type}</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Permission Violations" subtitle="Recent denied tool calls" />
        <CardBody className="p-0">
          {recent_denied_calls.length === 0 ? (
            <EmptyState>None — every tool call so far has been within its agent&apos;s permission.</EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {recent_denied_calls.map((c) => (
                <div key={c.id} className="px-5 py-2.5 text-sm flex items-center justify-between">
                  <span>
                    {c.agent_id} → {c.tool_name}
                  </span>
                  <span className="text-xs text-[var(--muted-foreground)]">{c.denial_reason}</span>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
