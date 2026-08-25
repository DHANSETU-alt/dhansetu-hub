import { getInitiatives } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

export const dynamic = "force-dynamic";

const STATUS_TONE: Record<string, "good" | "warn" | "neutral"> = {
  running: "good",
  paused: "warn",
  done: "neutral",
};

export default async function InitiativesPage() {
  const result = await getInitiatives().catch(() => null);

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

  const initiatives = result.initiatives;
  const running = initiatives.filter((i) => i.status === "running");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Founder Tasks</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Task 1, Task 2, ... — real, standing work the founder asked for. Percent complete is computed from real
            milestones below, never a hand-picked number. Multiple tasks can run at once — a new task doesn&apos;t
            pause an older one.
          </p>
        </div>
        <AutoRefresh intervalSeconds={20} />
      </div>

      {initiatives.length === 0 ? (
        <Card>
          <CardBody>
            <EmptyState>
              No tasks tracked yet. Use <code>--initiative-add &quot;TITLE&quot;</code> from the CLI to start Task 1.
            </EmptyState>
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-4">
          {initiatives.map((init) => (
            <Card key={init.id}>
              <CardHeader
                title={`Task ${init.seq} — ${init.title}`}
                subtitle={
                  init.artifact_url
                    ? `Linked artifact: ${init.artifact_url}`
                    : `${init.milestone_done}/${init.milestone_total} milestones done`
                }
                action={
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-semibold font-mono-num text-[var(--ink)]">
                      {init.percent_complete}%
                    </span>
                    <Badge tone={STATUS_TONE[init.status] ?? "neutral"}>{init.status}</Badge>
                  </div>
                }
              />
              <CardBody>
                <div className="h-2 rounded-full bg-[var(--surface-2)] overflow-hidden mb-5">
                  <div
                    className="h-full rounded-full bg-[var(--local)] transition-all"
                    style={{ width: `${init.percent_complete}%` }}
                  />
                </div>

                {init.artifact_url && (
                  <a
                    href={init.artifact_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-block text-xs text-[var(--local)] hover:underline mb-4"
                  >
                    Open linked artifact →
                  </a>
                )}

                {init.milestones.length === 0 ? (
                  <p className="text-xs text-[var(--muted-foreground)]">No milestones broken out yet.</p>
                ) : (
                  <div className="space-y-1.5">
                    {init.milestones.map((m) => (
                      <div key={m.id} className="flex items-center gap-2.5 text-sm">
                        <span
                          className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] shrink-0 ${
                            m.done
                              ? "bg-[var(--local-soft)] text-[var(--local)]"
                              : "border border-[var(--border)] text-transparent"
                          }`}
                        >
                          {m.done ? "✓" : ""}
                        </span>
                        <span className={m.done ? "text-[var(--muted-foreground)] line-through" : "text-[var(--ink)]"}>
                          {m.title}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {running.length > 0 && (
        <p className="text-xs text-[var(--muted-foreground)]">
          Currently running: {running.map((i) => `Task ${i.seq}`).join(", ")} — all active at once, side by side.
        </p>
      )}
    </div>
  );
}
