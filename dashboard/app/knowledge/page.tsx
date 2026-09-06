import { getKnowledge } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

export default async function KnowledgeExplorerPage() {
  const { documents } = await getKnowledge();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Knowledge Explorer</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Plain-text search (no embeddings) over SOPs, notes, and references — the Shakthi Knowledge agent answers from these.
          </p>
        </div>
        <AutoRefresh intervalSeconds={1} />
      </div>

      <Card>
        <CardHeader title="Documents" subtitle={`${documents.length} stored`} />
        <CardBody className="p-0">
          {documents.length === 0 ? (
            <EmptyState>
              No documents yet. Run <code>python3 -m orchestrator.cli --knowledge-add &quot;Title&quot; --content &quot;...&quot;</code>
            </EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {documents.map((d) => (
                <div key={d.id} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium">{d.title}</span>
                    <Badge tone="neutral">{d.category}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-[var(--muted-foreground)] max-w-[70ch] line-clamp-2">{d.content}</p>
                  {d.tags && <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">tags: {d.tags}</p>}
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
