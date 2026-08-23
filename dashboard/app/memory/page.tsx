import { getMemory } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

const LAYER_TONE: Record<string, "local" | "cloud" | "neutral"> = {
  strategic: "cloud", lesson: "cloud", business: "local", project: "local", session: "neutral",
};

export default async function MemoryExplorerPage() {
  const { entries } = await getMemory();
  const byLayer = entries.reduce<Record<string, typeof entries>>((acc, e) => {
    (acc[e.layer] ??= []).push(e);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Memory Explorer</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            What an agent actually retrieves before acting — recency-only (no embeddings yet), scoped per business.
          </p>
        </div>
        <AutoRefresh intervalSeconds={20} />
      </div>

      {entries.length === 0 ? (
        <Card>
          <CardBody>
            <EmptyState>No memory entries yet — written automatically after each task completes.</EmptyState>
          </CardBody>
        </Card>
      ) : (
        Object.entries(byLayer).map(([layer, layerEntries]) => (
          <Card key={layer}>
            <CardHeader title={layer.toUpperCase()} subtitle={`${layerEntries.length} entries`} />
            <CardBody className="p-0">
              <div className="divide-y divide-[var(--border)]">
                {layerEntries.map((e) => (
                  <div key={e.id} className="px-5 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm max-w-[65ch]">{e.content}</p>
                      <Badge tone={LAYER_TONE[e.layer] ?? "neutral"}>business {e.business_id ?? "—"}</Badge>
                    </div>
                    <div className="mt-1 flex items-center gap-3 text-xs text-[var(--muted-foreground)]">
                      {e.tags && <span>tags: {e.tags}</span>}
                      <span className="font-mono-num">{e.created_at}</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>
        ))
      )}
    </div>
  );
}
