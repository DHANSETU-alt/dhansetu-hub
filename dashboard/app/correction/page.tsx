import { getCorrections } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

const FINAL_STATUS_TONE: Record<string, "good" | "warn" | "bad"> = {
  approved: "good", revise: "warn",
};

const TASK_TYPE_LABEL: Record<string, string> = {
  code: "Code", writing: "Writing", business_report: "Business Report",
  website_content: "Website Content", seo_content: "SEO Content",
};

function avg(nums: (number | null)[]) {
  const vals = nums.filter((n): n is number => n !== null);
  if (!vals.length) return null;
  return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
}

export default async function CorrectionDashboardPage() {
  const { corrections } = await getCorrections(50);
  const completed = corrections.filter((c) => c.status === "completed");
  const avgCorrection = avg(completed.map((c) => c.correction_score));
  const avgQuality = avg(completed.map((c) => c.quality_score));
  const totalIssuesFound = completed.reduce((sum, c) => sum + c.issues_found, 0);
  const totalIssuesFixed = completed.reduce((sum, c) => sum + c.issues_fixed, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Correction Bot</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Senior Reviewer / Final Quality Controller. Task Complete → Correction Review → QA Review → Security Review → Final Approval.
            Runs automatically after Bug Fixer patches, Website Builder pipelines, and codebase audits.
          </p>
        </div>
        <AutoRefresh intervalSeconds={5} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Avg Correction Score" value={avgCorrection !== null ? `${avgCorrection}/100` : "—"}
                   tone={avgCorrection !== null && avgCorrection < 70 ? "warn" : "good"} />
        <StatTile label="Avg Quality Score" value={avgQuality !== null ? `${avgQuality}/100` : "—"}
                   tone={avgQuality !== null && avgQuality < 70 ? "warn" : "good"} />
        <StatTile label="Issues Found (total)" value={String(totalIssuesFound)} />
        <StatTile label="Issues Fixed (total)" value={String(totalIssuesFixed)} />
      </div>

      <Card>
        <CardHeader title="Correction History" subtitle={`${corrections.length} run(s)`} />
        <CardBody className="p-0">
          {corrections.length === 0 ? (
            <EmptyState>
              No corrections logged yet. Run{" "}
              <code>python3 -m orchestrator.cli --correct writing --content-file report.txt</code>
            </EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {corrections.map((c) => (
                <div key={c.id} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium">
                      #{c.id} · {TASK_TYPE_LABEL[c.task_type] ?? c.task_type}
                    </span>
                    <div className="flex items-center gap-2">
                      <Badge tone={c.status === "completed" ? "good" : c.status === "failed" ? "bad" : "warn"}>{c.status}</Badge>
                      {c.final_status && <Badge tone={FINAL_STATUS_TONE[c.final_status] ?? "neutral"}>{c.final_status}</Badge>}
                      {c.correction_score !== null && (
                        <Badge tone={c.correction_score >= 70 ? "good" : "bad"}>correction {c.correction_score}</Badge>
                      )}
                      {c.quality_score !== null && (
                        <Badge tone={c.quality_score >= 70 ? "good" : "bad"}>quality {c.quality_score}</Badge>
                      )}
                    </div>
                  </div>
                  <div className="mt-1.5 flex items-center gap-4 text-xs text-[var(--muted-foreground)]">
                    <span>{c.task_ref || "(no ref)"}</span>
                    <span>{c.issues_found} found · {c.issues_fixed} fixed</span>
                    <span>QA {c.qa_status ?? "—"} · Security {c.security_status ?? "—"}</span>
                    <span className="font-mono-num">{c.completed_at || c.created_at}</span>
                  </div>
                  {c.summary && <p className="mt-1.5 text-xs text-[var(--muted-foreground)] max-w-[70ch]">{c.summary}</p>}
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
