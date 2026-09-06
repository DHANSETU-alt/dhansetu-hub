import { getTasks } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

const STATUS_TONE: Record<string, "good" | "warn" | "bad"> = { done: "good", pending: "warn", failed: "bad" };

export default async function TaskPipelinePage() {
  const { tasks, counts } = await getTasks();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Task Pipeline</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Every task dispatched by any agent — dispatch → local model → QA → (escalate?) → done.
          </p>
        </div>
        <AutoRefresh intervalSeconds={1} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatTile label="Pending" value={String(counts.pending ?? 0)} tone={counts.pending ? "warn" : "good"} />
        <StatTile label="Done" value={String(counts.done ?? 0)} tone="good" />
        <StatTile label="Failed" value={String(counts.failed ?? 0)} tone={counts.failed ? "bad" : "good"} />
      </div>

      <Card>
        <CardHeader title="Recent Tasks" subtitle={`${tasks.length} shown, most recent first`} />
        <CardBody className="p-0">
          {tasks.length === 0 ? (
            <EmptyState>No tasks yet. Run any agent from the CLI to see it here.</EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)] max-h-[600px] overflow-y-auto">
              {tasks.map((t) => (
                <div key={t.id} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium truncate max-w-[60ch]">{t.goal}</span>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge tone={t.risk_level === "critical" ? "bad" : "neutral"}>{t.risk_level}</Badge>
                      <Badge tone={STATUS_TONE[t.status] ?? "neutral"}>{t.status}</Badge>
                    </div>
                  </div>
                  <div className="mt-1 flex items-center gap-4 text-xs text-[var(--muted-foreground)]">
                    <span>#{t.id}</span>
                    <span>{t.agent_id}</span>
                    <span>business {t.business_id ?? "—"}</span>
                    <span className="font-mono-num">{t.created_at}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
