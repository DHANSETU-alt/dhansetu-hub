import { getWebsiteProjects, getWebsites } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

const STATUS_TONE: Record<string, "good" | "warn" | "bad" | "neutral"> = {
  requested: "neutral", ceo_approved: "warn", ceo_rejected: "bad",
  requirements_ready: "warn", built: "warn", qa_passed: "warn", qa_failed: "bad",
  security_passed: "warn", security_failed: "bad", packaged: "good", failed: "bad",
};

const PIPELINE_STAGES = ["requested", "ceo_approved", "requirements_ready", "built", "qa_passed", "security_passed", "packaged"];

export default async function WebsiteBuilderPage() {
  const [{ projects, templates }, { sites }] = await Promise.all([getWebsiteProjects(), getWebsites()]);
  const packaged = projects.filter((p) => p.status === "packaged").length;
  const failed = projects.filter((p) => p.status.includes("failed") || p.status === "ceo_rejected").length;
  const inProgress = projects.length - packaged - failed;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Website Builder</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Founder Request → CEO Review → Requirements → Build → QA → Security → Deployment Package.
          </p>
        </div>
        <AutoRefresh intervalSeconds={15} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Projects" value={String(projects.length)} />
        <StatTile label="In Progress" value={String(inProgress)} tone={inProgress ? "warn" : "good"} />
        <StatTile label="Packaged" value={String(packaged)} tone="good" />
        <StatTile label="Failed / Rejected" value={String(failed)} tone={failed ? "bad" : "good"} />
      </div>

      <Card>
        <CardHeader title="Templates" subtitle={`${templates.length} site types registered`} />
        <CardBody className="flex flex-wrap gap-2">
          {templates.map((t) => (
            <span key={t} className="text-sm rounded-md border border-[var(--border)] px-3 py-1 capitalize">
              {t.replace(/_/g, " ")}
            </span>
          ))}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Projects" subtitle="Build status per project" />
        <CardBody className="p-0">
          {projects.length === 0 ? (
            <EmptyState>
              None yet. Run <code>python3 -m orchestrator.cli --website-build landing_page --business 1 --request &quot;...&quot;</code>
            </EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {projects.map((p) => (
                <div key={p.id} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium max-w-[50ch] truncate">{p.founder_request}</span>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge tone="neutral">{p.site_type.replace(/_/g, " ")}</Badge>
                      <Badge tone={STATUS_TONE[p.status] ?? "neutral"}>{p.status.replace(/_/g, " ")}</Badge>
                    </div>
                  </div>
                  <div className="mt-1.5 flex items-center gap-1">
                    {PIPELINE_STAGES.map((stage, i) => {
                      const stageIndex = PIPELINE_STAGES.indexOf(p.status);
                      const reached = stageIndex >= i;
                      const isFailure = p.status.includes("failed") || p.status === "ceo_rejected";
                      return (
                        <div
                          key={stage}
                          className="h-1.5 flex-1 rounded-full"
                          style={{ background: reached ? (isFailure && stageIndex === i ? "var(--bad)" : "var(--local)") : "var(--border)" }}
                          title={stage}
                        />
                      );
                    })}
                  </div>
                  <div className="mt-1.5 flex items-center gap-4 text-xs text-[var(--muted-foreground)]">
                    <span>#{p.id}</span>
                    <span>{p.business_name}</span>
                    {p.security_score !== null && <span>security {p.security_score}/100</span>}
                    {p.deployment_package_path && <span className="text-[var(--good)]">package ready</span>}
                    <span className="font-mono-num">{p.updated_at}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Generated Sites" subtitle="From both the Website Builder pipeline and the original single-template foundation" />
        <CardBody className="p-0">
          {sites.filter((s) => s.status !== "planned").length === 0 ? (
            <EmptyState>No sites generated yet.</EmptyState>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--muted-foreground)] border-b border-[var(--border)]">
                  <th className="px-5 py-2 font-medium">Business</th>
                  <th className="px-5 py-2 font-medium">Domain</th>
                  <th className="px-5 py-2 font-medium">Template</th>
                  <th className="px-5 py-2 font-medium">Status</th>
                  <th className="px-5 py-2 font-medium">File</th>
                </tr>
              </thead>
              <tbody>
                {sites.filter((s) => s.status !== "planned").map((s) => (
                  <tr key={s.id} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-5 py-2">{s.business_name}</td>
                    <td className="px-5 py-2 text-[var(--muted-foreground)]">{s.domain}</td>
                    <td className="px-5 py-2 text-[var(--muted-foreground)]">{s.template_id}</td>
                    <td className="px-5 py-2"><Badge tone="neutral">{s.status}</Badge></td>
                    <td className="px-5 py-2"><Badge tone={s.file_exists ? "good" : "bad"}>{s.file_exists ? "present" : "missing"}</Badge></td>
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
