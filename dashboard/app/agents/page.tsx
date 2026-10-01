import { getAgents, getAgentReality } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

const LAYER_TONE: Record<string, "local" | "cloud" | "neutral"> = {
  executive: "cloud",
  governance: "neutral",
  intelligence: "neutral",
};

export default async function AgentRegistryPage() {
  const [{ agents }, reality] = await Promise.all([getAgents(), getAgentReality().catch(() => null)]);
  const byLayer = agents.reduce<Record<string, typeof agents>>((acc, a) => {
    (acc[a.layer] ??= []).push(a);
    return acc;
  }, {});

  const claudeCalls = reality?.provider_counts.claude ?? 0;
  const ollamaCalls = reality?.provider_counts.ollama ?? 0;
  const totalCalls = claudeCalls + ollamaCalls;
  const fallbackCount = reality?.status_counts.done_local_fallback ?? 0;
  const failedCount = reality?.status_counts.failed ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Agent Registry</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Every agent is a config row, not a deployed service — adding the 12th agent is a yaml file, not code.
          </p>
        </div>
        <AutoRefresh intervalSeconds={5} />
      </div>

      <Card>
        <CardHeader
          title="Is it really agents working, or only Claude?"
          subtitle="All-time real counts from the tasks and cost_ledger tables — not a sample, not an estimate. Replaces the static architecture-diagram.html, which showed the code path, not whether it's actually exercised."
        />
        <CardBody>
          {reality ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatTile
                  label="Ollama calls (local)"
                  value={totalCalls ? `${Math.round((ollamaCalls / totalCalls) * 100)}%` : "—"}
                  hint={`${ollamaCalls} of ${totalCalls} real model calls, all time`}
                  tone="good"
                />
                <StatTile
                  label="Claude calls (cloud)"
                  value={totalCalls ? `${Math.round((claudeCalls / totalCalls) * 100)}%` : "—"}
                  hint={claudeCalls === 0 ? "Zero, all time" : `${claudeCalls} of ${totalCalls}`}
                  tone={claudeCalls === 0 ? "warn" : "neutral"}
                />
                <StatTile
                  label="Failed cloud escalations"
                  value={`${fallbackCount}`}
                  hint="Attempted Claude, fell back to local"
                  tone={fallbackCount > 0 ? "warn" : "good"}
                />
                <StatTile
                  label="Agents ever run"
                  value={reality ? `${reality.ever_run_agent_count}/${reality.total_agents}` : "—"}
                  hint={`${reality.never_run_agents.length} registered, never dispatched once`}
                  tone={reality.ever_run_agent_count < reality.total_agents / 2 ? "warn" : "good"}
                />
              </div>

              <div className="rounded-md border border-[var(--border)] bg-black/20 p-3 text-xs text-[var(--muted-foreground)] space-y-1">
                <p>
                  <b className="text-[var(--ink)]">The honest answer:</b> every real model call this system has ever logged went to the local
                  Ollama model on {reality.ever_run_agent_count} distinct agent personas — real, distinct system prompts, not one generic
                  chatbot. {claudeCalls === 0 && (
                    <>Claude has <b className="text-[var(--warn)]">never</b> successfully run a task — {fallbackCount} tasks attempted cloud
                    escalation and fell back to local every time, because <code>ANTHROPIC_API_KEY</code> is{" "}
                    {reality.anthropic_key_configured ? "configured but calls still failed" : "not set on this Mac"}.</>
                  )}
                </p>
                <p>
                  It is also <b className="text-[var(--ink)]">not autonomous multi-agent execution</b> — <code>routing.run_task()</code> is one
                  synchronous dispatcher: pick a persona → call local model → at most one tool call → done. No parallelism, no continuous
                  agent loop. {reality.never_run_agents.length} of {reality.total_agents} registered agents (including an entire duplicate
                  &quot;Team 2&quot; roster) have never been dispatched once.
                </p>
              </div>

              {reality.never_run_agents.length > 0 && (
                <details className="text-xs text-[var(--muted-foreground)]">
                  <summary className="cursor-pointer text-[var(--ink)]">Never-run agents ({reality.never_run_agents.length})</summary>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {reality.never_run_agents.map((a) => (
                      <span key={a.id} className="text-[11px] rounded bg-[var(--surface-2)] px-1.5 py-0.5">{a.name}</span>
                    ))}
                  </div>
                </details>
              )}
            </div>
          ) : (
            <EmptyState>Reality-check API unavailable.</EmptyState>
          )}
        </CardBody>
      </Card>

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
