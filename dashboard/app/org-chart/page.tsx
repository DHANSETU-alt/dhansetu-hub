import { getAgents } from "@/lib/api";
import { Card, CardHeader, CardBody, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";
import { OrgChartFlow } from "@/components/OrgChartFlow";

export const dynamic = "force-dynamic";

export default async function OrgChartPage() {
  const result = await getAgents().catch(() => null);

  if (!result) {
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

  const agents = result.agents;

  return (
    <div className="space-y-4 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Org Chart</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            One Angella, two CEO-led teams — {agents.length} real registered agents, from the actual agent registry, not illustrative.
          </p>
        </div>
        <AutoRefresh intervalSeconds={30} />
      </div>

      {agents.length === 0 ? (
        <Card>
          <CardBody>
            <EmptyState>No agents registered yet.</EmptyState>
          </CardBody>
        </Card>
      ) : (
        <div className="flex-1 min-h-[70vh] rounded-xl border border-[var(--border)] overflow-hidden" style={{ background: "#020303" }}>
          <OrgChartFlow agents={agents} />
        </div>
      )}
    </div>
  );
}
