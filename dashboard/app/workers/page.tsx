import { getWorkers } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

const WORKER_STATUS_TONE: Record<string, "good" | "warn" | "bad"> = { idle: "good", busy: "warn", failed: "bad" };
const QUEUE_STATUS_TONE: Record<string, "good" | "warn" | "bad" | "neutral"> = {
  done: "good", running: "warn", failed: "bad", queued: "neutral",
};
const TYPE_LABEL: Record<string, string> = { rapid: "Rapid Worker", engineering: "Engineering Worker", infra: "Infra Worker" };

export default async function WorkersDashboardPage() {
  const { workers, load_balancer, queue } = await getWorkers(50);
  const active = workers.filter((w) => w.status === "busy").length;
  const completedTotal = workers.reduce((sum, w) => sum + w.tasks_completed, 0);
  const failedTotal = workers.reduce((sum, w) => sum + w.tasks_failed, 0);

  const byType = ["rapid", "engineering", "infra"].map((t) => ({
    type: t, workers: workers.filter((w) => w.worker_type === t),
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Worker Pool</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Rapid / Engineering / Infra workers assist CEO, Finance, Security, Sentinel, Bug Fixer, Engineer, Website
            Builder, and Chrome Developer — real parallel execution (ThreadPoolExecutor), never a business decision.
          </p>
        </div>
        <AutoRefresh intervalSeconds={1} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Queue Depth" value={String(load_balancer.queue_depth)}
                   tone={load_balancer.overflowing ? "bad" : load_balancer.scaled_up ? "warn" : "good"} />
        <StatTile label="Active Workers" value={String(active)} />
        <StatTile label="Completed Tasks" value={String(completedTotal)} tone="good" />
        <StatTile label="Failed Tasks" value={String(failedTotal)} tone={failedTotal ? "warn" : "good"} />
      </div>

      <Card>
        <CardHeader title="Load Balancer Status"
                     subtitle={`threshold ${load_balancer.scale_threshold} · max ${load_balancer.max_queue_size} · ${load_balancer.scaled_up ? "scaled up" : "base concurrency"}${load_balancer.overflowing ? " · OVERFLOWING" : ""}`} />
        <CardBody>
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(load_balancer.concurrency).map(([type, n]) => (
              <StatTile key={type} label={`${TYPE_LABEL[type] ?? type} concurrency`} value={String(n)} />
            ))}
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Worker Status" subtitle={`${workers.length} registered`} />
        <CardBody className="p-0">
          {workers.length === 0 ? (
            <EmptyState>
              No workers registered yet. Run <code>python3 -m orchestrator.cli --worker-status</code>
            </EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {byType.map(({ type, workers: typeWorkers }) => (
                <div key={type} className="px-5 py-3">
                  <div className="text-xs uppercase tracking-wide text-[var(--muted-foreground)] mb-2">{TYPE_LABEL[type]}</div>
                  <div className="flex flex-wrap gap-2">
                    {typeWorkers.map((w) => (
                      <div key={w.id} className="flex items-center gap-2 rounded-lg border border-[var(--border)] px-2.5 py-1.5 text-xs">
                        <span className="font-mono-num">{w.name}</span>
                        <Badge tone={WORKER_STATUS_TONE[w.status] ?? "neutral"}>{w.status}</Badge>
                        <span className="text-[var(--muted-foreground)]">{w.tasks_completed}✓ {w.tasks_failed}✗</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Task Queue" subtitle={`${queue.length} recent`} />
        <CardBody className="p-0">
          {queue.length === 0 ? (
            <EmptyState>
              No tasks queued yet. Run{" "}
              <code>python3 -m orchestrator.cli --worker-enqueue website_audit --payload-json {"'"}{"{"}"url": "https://example.com"{"}"}{"'"}</code>
            </EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {queue.map((q) => (
                <div key={q.id} className="px-5 py-3 flex items-center justify-between gap-3">
                  <span className="text-sm">#{q.id} · {q.kind}</span>
                  <div className="flex items-center gap-3 text-xs text-[var(--muted-foreground)]">
                    <span>{q.assigned_worker_type ?? "—"}</span>
                    <Badge tone={QUEUE_STATUS_TONE[q.status] ?? "neutral"}>{q.status}</Badge>
                    <span className="font-mono-num">{q.completed_at || q.started_at || q.created_at}</span>
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
