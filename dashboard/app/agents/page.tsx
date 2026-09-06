import { getAgents } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

const LAYER_TONE: Record<string, "local" | "cloud" | "neutral"> = {
  executive: "cloud",
  governance: "neutral",
  intelligence: "neutral",
};

export default async function AgentRegistryPage() {
  const { agents } = await getAgents();
  const byLayer = agents.reduce<Record<string, typeof agents>>((acc, a) => {
    (acc[a.layer] ??= []).push(a);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Agent Registry</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Every agent is a config row, not a deployed service — adding the 12th agent is a yaml file, not code.
          </p>
        </div>
        <AutoRefresh intervalSeconds={30} />
      </div>

      {Object.entries(byLayer).map(([layer, layerAgents]) => (
        <Card key={layer}>
          <CardHeader title={layer.toUpperCase()} subtitle={`${layerAgents.length} agent(s)`} />
          <CardBody className="grid md:grid-cols-2 gap-3">
            {layerAgents.map((a) => (
              <div key={a.id} className="rounded-md border border-[var(--border)] p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{a.name}</span>
                  <Badge tone={a.default_model_tier === "cloud" ? "cloud" : "local"}>{a.default_model_tier}</Badge>
                </div>
                <div className="text-xs text-[var(--muted-foreground)] mt-1">
                  id: {a.id} · model: {a.local_model ?? "—"} · scope: {a.allowed_scope}
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {a.allowed_tools.length === 0 ? (
                    <span className="text-xs text-[var(--muted-foreground)]">no tools</span>
                  ) : (
                    a.allowed_tools.map((t) => (
                      <span key={t} className="text-[11px] rounded bg-[var(--surface-2)] px-1.5 py-0.5 text-[var(--muted-foreground)]">
                        {t}
                      </span>
                    ))
                  )}
                </div>
              </div>
            ))}
          </CardBody>
        </Card>
      ))}
    </div>
  );
}
