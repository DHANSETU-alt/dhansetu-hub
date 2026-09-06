import { getAudits } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

const AUDIT_STATUS_TONE: Record<string, "good" | "warn" | "bad"> = {
  completed: "good", running: "warn", failed: "bad",
};

export default async function AuditDashboardPage() {
  const { audits } = await getAudits();
  const latest = audits[0];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Audit History</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            CEO → Security → Bug Fixer → Engineer → CEO. Scope: orchestrator/**/*.py — the TypeScript dashboard isn&apos;t covered.
          </p>
        </div>
        <AutoRefresh intervalSeconds={1} />
      </div>

      {latest && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatTile label="Latest Severity Score" value={latest.severity_score !== null ? `${latest.severity_score}/100` : "—"}
                     tone={latest.severity_score !== null && latest.severity_score < 70 ? "warn" : "good"} />
          <StatTile label="Latest Findings" value={String(latest.findings_count)} />
          <StatTile label="Files Affected" value={String(latest.files_affected)} />
          <StatTile label="Total Audits Run" value={String(audits.length)} />
        </div>
      )}

      <Card>
        <CardHeader title="Audit Runs" />
        <CardBody className="p-0">
          {audits.length === 0 ? (
            <EmptyState>
              No audits run yet. Run <code>python3 -m orchestrator.cli --audit-run</code>
            </EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {audits.map((a) => (
                <div key={a.id} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium">Audit #{a.id}</span>
                    <div className="flex items-center gap-2">
                      <Badge tone={AUDIT_STATUS_TONE[a.status] ?? "neutral"}>{a.status}</Badge>
                      {a.severity_score !== null && (
                        <Badge tone={a.severity_score >= 70 ? "good" : "bad"}>score {a.severity_score}</Badge>
                      )}
                    </div>
                  </div>
                  <div className="mt-1.5 flex items-center gap-4 text-xs text-[var(--muted-foreground)]">
                    <span>{a.findings_count} findings</span>
                    <span>{a.files_affected} files affected</span>
                    <span className="font-mono-num">{a.completed_at || a.created_at}</span>
                  </div>
                  {a.executive_summary && <p className="mt-1.5 text-xs text-[var(--muted-foreground)] max-w-[70ch]">{a.executive_summary}</p>}
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
