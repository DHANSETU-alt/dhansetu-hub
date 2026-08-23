import { getOverview } from "@/lib/api";
import { Card, CardHeader, CardBody, ComingSoon } from "@/components/ui";

export default async function WorkspaceManagerPage() {
  const overview = await getOverview().catch(() => null);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Business Workspace Manager</h1>
      <Card>
        <CardHeader title="Businesses" subtitle="Read-only list — this is the full manager for now" />
        <CardBody className="flex flex-wrap gap-2">
          {overview?.businesses.map((b) => (
            <span key={b.id} className="text-sm rounded-md border border-[var(--border)] px-3 py-1">
              #{b.id} {b.name}
            </span>
          )) ?? <span className="text-sm text-[var(--muted-foreground)]">API unreachable</span>}
        </CardBody>
      </Card>
      <ComingSoon
        title="Full Workspace Manager"
        note="Creating/renaming businesses, per-business settings (tax rate, currency, timezone), and inviting collaborators once multi-tenancy is real — today businesses are managed via orchestrator/seed.py and direct DB access."
      />
    </div>
  );
}
