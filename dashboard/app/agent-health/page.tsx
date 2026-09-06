import { getAgentHealth } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";
import type { AgentHealth } from "@/lib/api";

// Real signals only: task_count/failed_count/last_activity come straight
// from the tasks table (same window report_generators.agent_health_report_text()
// already used, limit 200 recent tasks system-wide). No per-agent latency
// or escalation-rate tracker exists in this system yet, so this page
// doesn't claim to show one -- see /api/agent-health's own comment.
function statusFor(a: AgentHealth): { label: string; tone: "good" | "warn" | "bad" | "neutral" } {
  if (!a.local_model) return { label: "No model configured", tone: "bad" };
  if (a.task_count === 0) return { label: "Never run", tone: "neutral" };
  if (a.failed_count > 0 && a.failed_count === a.task_count) return { label: "All recent tasks failed", tone: "bad" };
  if (a.failed_count > 0) return { label: `${a.failed_count} recent failure(s)`, tone: "warn" };
  return { label: "Healthy", tone: "good" };
}

function timeAgo(iso: string | null): string {
  if (!iso) return "never";
  const then = new Date(iso.replace(" ", "T") + "Z").getTime();
  const diffMs = Date.now() - then;
  const days = Math.floor(diffMs / 86_400_000);
  if (days > 0) return `${days}d ago`;
  const hours = Math.floor(diffMs / 3_600_000);
  if (hours > 0) return `${hours}h ago`;
  const mins = Math.floor(diffMs / 60_000);
  return mins > 0 ? `${mins}m ago` : "just now";
}

export default async function AgentHealthPage() {
  const { agents, window: statWindow } = await getAgentHealth();
  const byLayer = agents.reduce<Record<string, AgentHealth[]>>((acc, a) => {
    (acc[a.layer] ??= []).push(a);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Agent Health Monitor</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Real task activity per agent ({statWindow}) -- registration + recent-run status, not a live uptime probe.
          </p>
        </div>
        <AutoRefresh intervalSeconds={1} />
      </div>

      {Object.entries(byLayer).map(([layer, layerAgents]) => (
        <Card key={layer}>
          <CardHeader title={layer.toUpperCase()} subtitle={`${layerAgents.length} agent(s)`} />
          <CardBody className="grid md:grid-cols-2 gap-3">
            {layerAgents.map((a) => {
              const status = statusFor(a);
              return (
                <div key={a.id} className="rounded-md border border-[var(--border)] p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm">{a.name}</span>
                    <Badge tone={status.tone}>{status.label}</Badge>
                  </div>
                  <div className="text-xs text-[var(--muted-foreground)] mt-1">
                    {a.task_count} recent task(s) · last activity {timeAgo(a.last_activity)}
                  </div>
                  <div className="text-xs text-[var(--muted-foreground)] mt-0.5">
                    model: {a.local_model ?? "none"} ({a.default_model_tier})
                  </div>
                </div>
              );
            })}
          </CardBody>
        </Card>
      ))}
    </div>
  );
}
