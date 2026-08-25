import {
  getCeoHealth, getWorkers, getFinanceAll, getSecurityLatest, getBugs,
  getWebsiteReviews, getWebsiteProjects, getKnowledge, getTasks, getSentinelLatest, getAgents,
} from "@/lib/api";

// Shared by Mission Control and blackboxOps_OS's agent visualization -- both
// render the exact same real backend (there is one orchestrator, not two;
// blackboxOps_OS's "Agent Visualization" is a rebranded view of the same
// live system, not a separate implementation).

export const ACTIVITY_WINDOW_MINUTES = 30;

function isRecent(timestamp: string | undefined | null): boolean {
  if (!timestamp) return false;
  const t = new Date(timestamp.includes("Z") ? timestamp : timestamp + "Z").getTime();
  return Date.now() - t < ACTIVITY_WINDOW_MINUTES * 60 * 1000;
}

function mostRecent(timestamps: (string | null | undefined)[]): string | null {
  const real = timestamps.filter((t): t is string => !!t).sort().reverse();
  return real[0] ?? null;
}

export type AgentNode = {
  id: string;
  name: string;
  squad: string | null;
  layer: string;
  active: boolean;
  sublabel: string;
  color: "cyan" | "violet" | "amber" | "rose" | "emerald" | "slate";
};

export async function loadSystemStatus() {
  const [ceoHealth, workers, financeAll, securityLatest, bugsOpen, reviews, projects, knowledge, tasks, sentinelLatest, agentsResp] =
    await Promise.all([
      getCeoHealth(),
      getWorkers(50),
      getFinanceAll("daily").catch(() => null),
      getSecurityLatest().catch(() => null),
      getBugs("open").catch(() => ({ bugs: [] })),
      getWebsiteReviews(10).catch(() => ({ reviews: [] })),
      getWebsiteProjects().catch(() => ({ projects: [], templates: [] })),
      getKnowledge().catch(() => ({ documents: [] })),
      getTasks().catch(() => ({ tasks: [], counts: {} })),
      getSentinelLatest().catch(() => ({ snapshot: null, services: null })),
      getAgents().catch(() => ({ agents: [] })),
    ]);

  const totalRevenue = financeAll?.reports?.reduce((sum, r) => sum + (r.report?.revenue_usd || 0), 0) ?? 0;

  // Real per-agent activity from the one shared tasks feed -- every agent,
  // not just the handful that used to have their own hand-picked signal.
  // Bounded by /api/tasks' own 100-row window (most-recent-system-wide,
  // not per-agent): a low-traffic agent's last real task can fall outside
  // that window if other agents have been busier. Honest known limit, not
  // hidden -- the same tradeoff every "recent activity" signal on this
  // page already accepts.
  const tasksByAgent = new Map<string, typeof tasks.tasks>();
  for (const t of tasks.tasks) {
    const list = tasksByAgent.get(t.agent_id) ?? [];
    list.push(t);
    tasksByAgent.set(t.agent_id, list);
  }
  const lastTaskAt = (agentId: string) => mostRecent((tasksByAgent.get(agentId) ?? []).map((t) => t.created_at));
  const taskCount = (agentId: string) => (tasksByAgent.get(agentId) ?? []).length;

  const avgSeo = reviews.reviews.length
    ? Math.round(
        reviews.reviews.filter((r) => r.seo_score !== null).reduce((s, r) => s + (r.seo_score || 0), 0) /
          (reviews.reviews.filter((r) => r.seo_score !== null).length || 1)
      )
    : null;

  // Rich, dedicated signal where this project already has one; every other
  // real agent (the 10 added this session with no bespoke metric yet --
  // sales, marketing, customer_success, correction_bot, buddy,
  // data_intelligence, engineer, qa, memory, manager) falls back to a
  // generic "how many real tasks has it actually run" signal instead of
  // being left off the chart, which is the whole point of this rebuild.
  const RICH: Record<string, () => { active: boolean; sublabel: string; color: AgentNode["color"] }> = {
    // Her signature color is always cyan -- a fixed brand identity, not a
    // generic "cyan when active, slate when idle" fallback -- matching the
    // design brief saved to the knowledge base. Only the pulse (active)
    // reflects whether she's actually done something in the last 30 min.
    pa_angella: () => {
      const active = isRecent(lastTaskAt("pa_angella"));
      return { active, sublabel: active ? "Refining" : "Standing by", color: "cyan" };
    },
    ceo: () => ({
      active: isRecent(lastTaskAt("ceo")), sublabel: ceoHealth.status.toUpperCase(),
      color: ceoHealth.status === "healthy" ? "emerald" : ceoHealth.status === "degraded" ? "amber" : "rose",
    }),
    finance: () => ({ active: isRecent(lastTaskAt("finance")), sublabel: `$${totalRevenue.toFixed(0)}`, color: "amber" }),
    security: () => ({
      active: isRecent(securityLatest?.latest_report?.created_at),
      sublabel: securityLatest?.latest_report?.score != null ? `${securityLatest.latest_report.score}/100` : "—",
      color: securityLatest?.latest_report?.score != null && securityLatest.latest_report.score < 70 ? "rose" : "emerald",
    }),
    bug_fixer: () => ({
      active: isRecent(lastTaskAt("bug_fixer")), sublabel: `${bugsOpen.bugs.length} open`,
      color: bugsOpen.bugs.length > 0 ? "rose" : "emerald",
    }),
    chrome_developer: () => ({
      active: isRecent(mostRecent(reviews.reviews.map((r) => r.created_at))),
      sublabel: avgSeo !== null ? `SEO ${avgSeo}` : "—", color: "violet",
    }),
    website_builder: () => ({
      active: isRecent(mostRecent(projects.projects.map((p) => p.created_at))),
      sublabel: `${projects.projects.length} sites`, color: "violet",
    }),
    knowledge: () => ({
      active: isRecent(mostRecent(knowledge.documents.map((d) => d.created_at))),
      sublabel: `${knowledge.documents.length} docs`, color: "slate",
    }),
  };

  const agents = agentsResp.agents;
  const nodes: AgentNode[] = agents.map((a) => {
    const rich = RICH[a.id]?.();
    if (rich) return { id: a.id, name: a.name, squad: a.squad, layer: a.layer, ...rich };
    const count = taskCount(a.id);
    const active = isRecent(lastTaskAt(a.id));
    return {
      id: a.id, name: a.name, squad: a.squad, layer: a.layer, active,
      sublabel: count > 0 ? `${count} task${count === 1 ? "" : "s"}` : "(idle)",
      color: active ? "cyan" : "slate",
    };
  });

  return {
    nodes,
    ceoHealth,
    bugsOpen,
    workers: workers.workers,
    loadBalancer: workers.load_balancer,
    sentinelOk: !!sentinelLatest.snapshot,
  };
}
