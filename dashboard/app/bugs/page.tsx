import { getBugs } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

const SEVERITY_TONE: Record<string, "bad" | "warn" | "neutral"> = {
  P0: "bad", P1: "bad", P2: "warn", P3: "neutral", P4: "neutral",
};

const STATUS_TONE: Record<string, "good" | "warn" | "bad" | "neutral"> = {
  open: "warn", analyzing: "warn", patch_proposed: "warn", ceo_approved: "warn",
  fix_applied: "good", verified: "good", regressed: "bad", ceo_rejected: "bad", closed: "neutral",
};

export default async function BugDashboardPage() {
  const { bugs } = await getBugs();

  const open = bugs.filter((b) => !["verified", "closed", "ceo_rejected"].includes(b.status)).length;
  const critical = bugs.filter((b) => b.severity === "P0" || b.severity === "P1").length;
  const regressed = bugs.filter((b) => b.status === "regressed").length;
  const verified = bugs.filter((b) => b.status === "verified").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Bug Dashboard</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Staff-Engineer-style pipeline: analyze → propose (staged, never live) → QA → Security → CEO → apply → verify.
          </p>
        </div>
        <AutoRefresh intervalSeconds={5} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Open" value={String(open)} tone={open > 0 ? "warn" : "good"} />
        <StatTile label="P0/P1 Critical" value={String(critical)} tone={critical > 0 ? "bad" : "good"} />
        <StatTile label="Verified Fixed" value={String(verified)} tone="good" />
        <StatTile label="Regressed" value={String(regressed)} tone={regressed > 0 ? "bad" : "good"} />
      </div>

      <Card>
        <CardHeader title="Bug History" subtitle={`${bugs.length} tracked, most recent first`} />
        <CardBody className="p-0">
          {bugs.length === 0 ? (
            <EmptyState>
              No bugs tracked yet. Run <code>python3 -m orchestrator.cli --bug-scan</code> or file one with{" "}
              <code>--bug-report</code>.
            </EmptyState>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--muted-foreground)] border-b border-[var(--border)]">
                  <th className="px-5 py-2 font-medium">ID</th>
                  <th className="px-5 py-2 font-medium">Severity</th>
                  <th className="px-5 py-2 font-medium">Title</th>
                  <th className="px-5 py-2 font-medium">File</th>
                  <th className="px-5 py-2 font-medium">Status</th>
                  <th className="px-5 py-2 font-medium">Occ.</th>
                  <th className="px-5 py-2 font-medium">Reg.</th>
                </tr>
              </thead>
              <tbody>
                {bugs.map((b) => (
                  <tr key={b.id} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-5 py-2 font-mono-num text-[var(--muted-foreground)]">#{b.id}</td>
                    <td className="px-5 py-2">
                      <Badge tone={SEVERITY_TONE[b.severity] ?? "neutral"}>{b.severity}</Badge>
                    </td>
                    <td className="px-5 py-2 max-w-[360px] truncate" title={b.title}>{b.title}</td>
                    <td className="px-5 py-2 text-[var(--muted-foreground)] text-xs">
                      {b.file_path ? `${b.file_path}${b.line_number ? `:${b.line_number}` : ""}` : "—"}
                    </td>
                    <td className="px-5 py-2">
                      <Badge tone={STATUS_TONE[b.status] ?? "neutral"}>{b.status}</Badge>
                    </td>
                    <td className="px-5 py-2 font-mono-num">{b.occurrence_count}</td>
                    <td className="px-5 py-2 font-mono-num">{b.regression_count}</td>
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
