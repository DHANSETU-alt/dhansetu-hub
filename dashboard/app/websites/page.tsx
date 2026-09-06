import { getWebsites } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

export default async function WebsiteMonitoringPage() {
  const { sites } = await getWebsites();
  const generated = sites.filter((s) => s.status !== "planned");
  const healthy = generated.filter((s) => s.file_exists).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Website Monitoring</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            No live deployment exists yet — this checks local file presence, not real uptime/SSL.
          </p>
        </div>
        <AutoRefresh intervalSeconds={1} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatTile label="Total Sites (seeded)" value={String(sites.length)} />
        <StatTile label="Generated" value={String(generated.length)} />
        <StatTile label="File Present" value={`${healthy}/${generated.length}`} tone={healthy === generated.length ? "good" : "warn"} />
      </div>

      <Card>
        <CardHeader title="Generated Sites" />
        <CardBody className="p-0">
          {generated.length === 0 ? (
            <EmptyState>
              None generated yet. Run <code>python3 -m orchestrator.cli --generate-site --business 1</code>
            </EmptyState>
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
                {generated.map((s) => (
                  <tr key={s.id} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-5 py-2">{s.business_name}</td>
                    <td className="px-5 py-2 text-[var(--muted-foreground)]">{s.domain}</td>
                    <td className="px-5 py-2 text-[var(--muted-foreground)]">{s.template_id}</td>
                    <td className="px-5 py-2">
                      <Badge tone="neutral">{s.status}</Badge>
                    </td>
                    <td className="px-5 py-2">
                      <Badge tone={s.file_exists ? "good" : "bad"}>{s.file_exists ? "present" : "missing"}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Planned (not yet generated)" subtitle={`${sites.length - generated.length} sites`} />
        <CardBody className="flex flex-wrap gap-2">
          {sites
            .filter((s) => s.status === "planned")
            .slice(0, 40)
            .map((s) => (
              <span key={s.id} className="text-xs rounded border border-[var(--border)] px-2 py-1 text-[var(--muted-foreground)]">
                {s.domain}
              </span>
            ))}
        </CardBody>
      </Card>
    </div>
  );
}
