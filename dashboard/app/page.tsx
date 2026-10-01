import { getOverview, getGovernorStatus, getCeoHealth, getIncidents, getWorkers, getPaymentLinks, getSecurityLatest, getInitiatives, getMacRuntime, getLinuxRuntime, getAiUsage, getAgents, getAgentHealth } from "@/lib/api";
import { Card, CardHeader, CardBody, StatTile, Badge, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";
import { SystemCircuitDiagram } from "@/components/SystemCircuitDiagram";
import { SHAKTHI_OS_VERSION } from "@/lib/version";
import Link from "next/link";

export default async function ExecutiveDashboard() {
  const overview = await getOverview().catch(() => null);

  if (!overview) {
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

  const ollama = overview.cost_summary.find((c) => c.provider === "ollama");
  const claude = overview.cost_summary.find((c) => c.provider === "claude");

  const [governor, ceoHealth, incidentsResult, workersResult, paymentsResult, securityResult, initiativesResult, macRuntime, linuxRuntime, aiUsage, agentsResult, agentHealthResult] = await Promise.all([
    getGovernorStatus().catch(() => null),
    getCeoHealth().catch(() => null),
    getIncidents().catch(() => null),
    getWorkers(20).catch(() => null),
    getPaymentLinks(20).catch(() => null),
    getSecurityLatest().catch(() => null),
    // The Founder dashboard is the task ledger of record. Do not hide
    // completed or paused initiatives here: that made the Linux-to-Mac migration
    // look as if imported Mac tasks were missing even though they remained
    // present in the API and database.
    getInitiatives().catch(() => null),
    getMacRuntime().catch(() => null),
    getLinuxRuntime().catch(() => null),
    getAiUsage().catch(() => null),
    getAgents().catch(() => null),
    getAgentHealth().catch(() => null),
  ]);
  const allInitiatives = initiativesResult?.initiatives ?? [];
  const agentCount = agentsResult?.agents?.length ?? 0;
  // "Active recently" = real last_activity timestamp within 24h, from the
  // same tasks-table signal agent-health already uses -- not a fabricated
  // per-agent heartbeat (this system has no live agent process liveness).
  const activeAgentCount = (agentHealthResult?.agents ?? []).filter((a) => {
    if (!a.last_activity) return false;
    const ageMs = Date.now() - new Date(a.last_activity.replace(" ", "T") + "Z").getTime();
    return ageMs >= 0 && ageMs < 24 * 60 * 60 * 1000;
  }).length;
  const revenueMission = allInitiatives.find((initiative) => initiative.title.includes("Revenue Mission Engine"));
  const initiativeLabel = (track: string, seq: number) =>
    `${track === "os" ? "OS" : track === "project" ? "Project" : "Task"} ${seq}`;

  // This dashboard now runs on two machines (Mac + Linux mirror, wired
  // 2026-09-16) -- macRuntime.os/.hostname is a real sample of WHATEVER
  // machine is actually serving this request (socket.gethostname(),
  // platform.system(), never guessed), despite the "mac" in its route
  // name. Real bug this fixes: the badge/subtitle used to hardcode "Mac"
  // regardless, so the Linux mirror's own dashboard confusingly said
  // "Mac control center" / "running on this Mac installation" about
  // itself -- exactly what the founder flagged live.
  const hostLabel = macRuntime?.os === "Linux" ? "Linux" : macRuntime?.os === "Darwin" ? "Mac" : macRuntime?.os ?? "This host";

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="mb-2 flex flex-wrap gap-2"><Badge tone="local">{hostLabel} control center{macRuntime ? ` · ${macRuntime.hostname}` : ""}</Badge><Badge tone={macRuntime ? "good" : "bad"}>{macRuntime ? "Runtime connected" : "Runtime unavailable"}</Badge></div>
          <h1 className="text-2xl font-semibold tracking-tight">{SHAKTHI_OS_VERSION.osName} V{SHAKTHI_OS_VERSION.version} Working Board</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">Founder-level view of data stored and services running on this {hostLabel} installation.</p>
        </div>
        <AutoRefresh intervalSeconds={5} />
      </div>

      <nav className="work-shortcuts" aria-label="Working areas">
        <Link href="/initiatives"><strong>Founder tasks</strong><small>Review pending work and initiative status</small></Link>
        <Link href="/tasks"><strong>Task pipeline</strong><small>Inspect execution records and results</small></Link>
        <Link href="/command-center"><strong>Issue a command</strong><small>Submit work through the existing controls</small></Link>
        <a href="/architecture-diagram.html" target="_blank" rel="noopener"><strong>System architecture</strong><small>Static code-path diagram — how a task is designed to flow</small></a>
        <Link href="/agents"><strong>Is it really agents, or just Claude?</strong><small>Live answer: real provider split, agent utilization, all time</small></Link>
      </nav>

      <SystemCircuitDiagram macRuntime={macRuntime} linuxRuntime={linuxRuntime} agentCount={agentCount} activeAgentCount={activeAgentCount} />

      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader title={`${hostLabel} Runtime`} subtitle={macRuntime ? `Live local sample · ${macRuntime.hostname} · API :${macRuntime.api_port}` : `No current ${hostLabel} sample available`} action={<Badge tone={macRuntime ? "good" : "bad"}>{macRuntime ? "LIVE LOCAL" : "DISCONNECTED"}</Badge>} />
          <CardBody>
            {macRuntime ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <StatTile label="CPU" value={`${macRuntime.cpu_percent}%`} hint={`${macRuntime.logical_cpus ?? "—"} logical CPUs`} tone={macRuntime.cpu_percent > 90 ? "bad" : macRuntime.cpu_percent > 75 ? "warn" : "good"} />
                  <StatTile label="RAM" value={`${macRuntime.ram_percent}%`} hint={`${(macRuntime.ram_total_bytes / 1073741824).toFixed(1)} GiB total`} tone={macRuntime.ram_percent > 90 ? "bad" : macRuntime.ram_percent > 80 ? "warn" : "good"} />
                  <StatTile label="Disk" value={`${macRuntime.disk_percent}%`} hint={`${(macRuntime.disk_free_bytes / 1073741824).toFixed(0)} GiB free`} tone={macRuntime.disk_percent > 90 ? "bad" : macRuntime.disk_percent > 80 ? "warn" : "good"} />
                  <StatTile label="Battery" value={macRuntime.battery_percent === null ? "N/A" : `${macRuntime.battery_percent}%`} hint={macRuntime.battery_plugged === null ? "Not detected" : macRuntime.battery_plugged ? "AC connected" : "On battery"} tone={macRuntime.battery_plugged === false ? "warn" : "good"} />
                </div>
                <div className="grid gap-2 text-xs text-[var(--muted-foreground)] sm:grid-cols-2">
                  <div className="rounded-md border border-[var(--border)] bg-black/20 p-3"><span className="block text-[10px] uppercase tracking-wider">Host</span><span className="text-[var(--ink)]">{macRuntime.os} {macRuntime.kernel} · {macRuntime.architecture}</span></div>
                  <div className="rounded-md border border-[var(--border)] bg-black/20 p-3"><span className="block text-[10px] uppercase tracking-wider">Processor</span><span className="text-[var(--ink)]">{macRuntime.cpu_name}</span></div>
                  <div className="rounded-md border border-[var(--border)] bg-black/20 p-3 sm:col-span-2"><span className="block text-[10px] uppercase tracking-wider">GPU</span><span className={macRuntime.gpu.state === "CONNECTED" ? "text-[var(--good)]" : "text-[var(--warn)]"}>{macRuntime.gpu.state === "CONNECTED" ? macRuntime.gpu.name : `${macRuntime.gpu.state} — ${macRuntime.gpu.reason}`}</span></div>
                </div>
              </div>
            ) : <EmptyState>Mac runtime API did not return a sample. Stored business data below may still be available.</EmptyState>}
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Revenue Mission" subtitle="Execution progress, not planning completion" action={<Badge tone={revenueMission?.status === "running" ? "good" : "neutral"}>{revenueMission?.status ?? "unavailable"}</Badge>} />
          <CardBody>
            {revenueMission ? <>
              <div className="flex items-end justify-between"><span className="text-4xl font-semibold font-mono-num">{revenueMission.percent_complete}%</span><span className="text-xs text-[var(--muted-foreground)]">{revenueMission.milestone_done}/{revenueMission.milestone_total} milestones</span></div>
              <div className="mt-4 h-2 overflow-hidden rounded-full bg-[var(--surface-2)]"><div className="h-full rounded-full bg-[var(--local)]" style={{ width: `${revenueMission.percent_complete}%` }} /></div>
              <div className="mt-4 grid grid-cols-2 gap-2 text-xs"><div className="rounded-md border border-[var(--border)] p-3"><span className="block text-[var(--muted-foreground)]">Verified revenue</span><b className="mt-1 block text-lg">₹0</b></div><div className="rounded-md border border-[var(--border)] p-3"><span className="block text-[var(--muted-foreground)]">Next gate</span><b className="mt-1 block">Send 5 messages</b></div></div>
              <Link href="/initiatives" className="mt-4 inline-block text-xs text-[var(--local)] hover:underline">Open mission milestones →</Link>
            </> : <EmptyState>Revenue Mission initiative is unavailable.</EmptyState>}
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader
          title="Linux Compute Node"
          subtitle={linuxRuntime?.reachable ? `Live sample over SSH · ${linuxRuntime.hostname} · 192.168.31.27` : "Not reachable this sample -- no cached numbers shown"}
          action={<Badge tone={linuxRuntime?.reachable ? "good" : "bad"}>{linuxRuntime?.reachable ? "ONLINE" : "OFFLINE"}</Badge>}
        />
        <CardBody>
          <div className="mb-4 flex items-center justify-center gap-0">
            <span className="flex h-3 w-3 rounded-full bg-[var(--local)] shadow-[0_0_8px_2px_var(--local)]" />
            <span className="mx-2 text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">Mac</span>
            <div className="relative h-px w-32 overflow-hidden bg-[var(--border)] sm:w-56">
              {linuxRuntime?.reachable && (
                <span
                  className="absolute inset-y-0 w-8 bg-gradient-to-r from-transparent via-[var(--local)] to-transparent"
                  style={{ animation: "linux-flow-pulse 1.6s linear infinite", boxShadow: "0 0 8px 1px var(--local)" }}
                />
              )}
            </div>
            <span className="mx-2 text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">Linux</span>
            <span className={`flex h-3 w-3 rounded-full ${linuxRuntime?.reachable ? "bg-[var(--local)] shadow-[0_0_8px_2px_var(--local)]" : "bg-[var(--bad)]"}`} />
          </div>
          <style>{"@keyframes linux-flow-pulse { from { left: -2rem; } to { left: 100%; } }"}</style>

          {linuxRuntime?.reachable ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                <StatTile label="CPU" value={`${linuxRuntime.cpu_percent}%`} hint={`${linuxRuntime.logical_cpus ?? "—"} logical CPUs`} tone={linuxRuntime.cpu_percent > 90 ? "bad" : linuxRuntime.cpu_percent > 75 ? "warn" : "good"} />
                <StatTile label="RAM" value={`${linuxRuntime.ram_percent}%`} hint={`${(linuxRuntime.ram_total_bytes / 1073741824).toFixed(1)} GiB total`} tone={linuxRuntime.ram_percent > 90 ? "bad" : linuxRuntime.ram_percent > 80 ? "warn" : "good"} />
                <StatTile label="Int Disk" value={`${linuxRuntime.disk_percent}%`} hint={`${(linuxRuntime.disk_free_bytes / 1073741824).toFixed(0)}/${(linuxRuntime.disk_total_bytes / 1073741824).toFixed(0)} GiB free`} tone={linuxRuntime.disk_percent > 90 ? "bad" : linuxRuntime.disk_percent > 80 ? "warn" : "good"} />
                <StatTile
                  label="Ext Storage"
                  value={!linuxRuntime.ext_storage.present ? "N/A" : !linuxRuntime.ext_storage.mounted ? "Unmounted" : `${linuxRuntime.ext_storage.percent}%`}
                  hint={
                    !linuxRuntime.ext_storage.present
                      ? "no external drive detected"
                      : !linuxRuntime.ext_storage.mounted
                        ? `${(linuxRuntime.ext_storage.total_bytes / 1073741824).toFixed(0)} GiB, not mounted`
                        : `${(linuxRuntime.ext_storage.free_bytes! / 1073741824).toFixed(0)}/${(linuxRuntime.ext_storage.total_bytes / 1073741824).toFixed(0)} GiB free`
                  }
                  tone={!linuxRuntime.ext_storage.present ? "neutral" : !linuxRuntime.ext_storage.mounted ? "warn" : (linuxRuntime.ext_storage.percent ?? 0) > 90 ? "bad" : "good"}
                />
                <StatTile
                  label="GPU"
                  value={linuxRuntime.gpu.state === "CONNECTED" ? `${linuxRuntime.gpu.utilization_percent}%` : "N/A"}
                  hint={linuxRuntime.gpu.state === "CONNECTED" ? `${linuxRuntime.gpu.temperature_c}°C · ${linuxRuntime.gpu.mem_used_mb.toFixed(0)}/${linuxRuntime.gpu.mem_total_mb.toFixed(0)} MiB` : linuxRuntime.gpu.reason}
                  tone={linuxRuntime.gpu.state === "CONNECTED" ? "good" : "neutral"}
                />
              </div>
              <div className="grid gap-2 text-xs text-[var(--muted-foreground)] sm:grid-cols-2">
                <div className="rounded-md border border-[var(--border)] bg-black/20 p-3"><span className="block text-[10px] uppercase tracking-wider">Host</span><span className="text-[var(--ink)]">{linuxRuntime.os} {linuxRuntime.kernel} · {linuxRuntime.architecture}</span></div>
                <div className="rounded-md border border-[var(--border)] bg-black/20 p-3"><span className="block text-[10px] uppercase tracking-wider">GPU</span><span className={linuxRuntime.gpu.state === "CONNECTED" ? "text-[var(--good)]" : "text-[var(--warn)]"}>{linuxRuntime.gpu.state === "CONNECTED" ? linuxRuntime.gpu.name : `${linuxRuntime.gpu.state} — ${linuxRuntime.gpu.reason}`}</span></div>
              </div>
            </div>
          ) : (
            <EmptyState>{linuxRuntime && "error" in linuxRuntime ? `Linux node unreachable: ${linuxRuntime.error}` : "Linux node unreachable this sample."}</EmptyState>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="AI Usage Today"
          subtitle={aiUsage ? `Real counts from the cost ledger, ${aiUsage.date}` : "Usage API did not return a sample"}
          action={<Badge tone={aiUsage?.cloud.configured ? "good" : "neutral"}>{aiUsage?.cloud.configured ? "CLOUD CONFIGURED" : "LOCAL ONLY"}</Badge>}
        />
        <CardBody>
          {aiUsage ? (
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-md border border-[var(--border)] p-3">
                <span className="block text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">Claude (this system's API)</span>
                <b className="mt-1 block text-lg">{aiUsage.cloud.calls_today} calls</b>
                <span className="block text-xs text-[var(--muted-foreground)]">${aiUsage.cloud.cost_usd_today.toFixed(4)} spent today{aiUsage.cloud.daily_budget_usd ? ` of $${aiUsage.cloud.daily_budget_usd} budget (${aiUsage.cloud.budget_remaining_usd?.toFixed(2)} left)` : " · no daily budget configured"}</span>
                {aiUsage.cloud.note && <span className="mt-1 block text-[11px] text-[var(--warn)]">{aiUsage.cloud.note}</span>}
              </div>
              <div className="rounded-md border border-[var(--border)] p-3">
                <span className="block text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">ChatGPT</span>
                <b className="mt-1 block text-lg">Not integrated</b>
                <span className="block text-xs text-[var(--muted-foreground)]">{aiUsage.chatgpt.note}</span>
              </div>
              <div className="rounded-md border border-[var(--border)] p-3">
                <span className="block text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">Ollama (local, free)</span>
                <b className="mt-1 block text-lg">{aiUsage.local.calls_today} calls</b>
                <span className="block text-xs text-[var(--muted-foreground)]">{aiUsage.local.limit}</span>
                <span className="mt-1 block text-[11px] text-[var(--muted-foreground)]">
                  {aiUsage.local.estimated_remaining_calls_today !== null
                    ? `~${aiUsage.local.estimated_remaining_calls_today} more calls estimated today (${aiUsage.local.calculation_basis})`
                    : aiUsage.local.calculation_basis}
                </span>
              </div>
            </div>
          ) : <EmptyState>AI usage API did not return a sample.</EmptyState>}
        </CardBody>
      </Card>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Businesses" value={String(overview.businesses.length)} />
        <StatTile label="Registered Agents" value={String(overview.agent_count)} />
        <StatTile label="Active Tasks" value={String(overview.active_tasks)} tone={overview.active_tasks > 0 ? "warn" : "good"} />
        <StatTile
          label="Local vs Cloud Calls"
          value={`${ollama?.calls ?? 0} / ${claude?.calls ?? 0}`}
          hint="ollama / claude"
        />
      </div>

      <Card>
        <CardHeader title="Subsystem Status" subtitle="Live responses where connected; unavailable or stored signals remain explicitly marked" />
        <CardBody>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <Link href="/mission-control" className="block">
              <StatTile label="Governor" value={governor?.status ?? "—"} tone={governor?.status === "operational" ? "good" : governor ? "bad" : "neutral"} />
            </Link>
            <Link href="/ceo" className="block">
              <StatTile label="CEO Health" value={ceoHealth?.status ?? "—"} tone={ceoHealth?.status === "healthy" ? "good" : ceoHealth?.status === "degraded" ? "warn" : ceoHealth ? "bad" : "neutral"} />
            </Link>
            <Link href="/ert" className="block">
              <StatTile label="Open Incidents" value={incidentsResult ? String(incidentsResult.open_count) : "—"} tone={incidentsResult?.critical_count ? "bad" : incidentsResult?.open_count ? "warn" : "good"} />
            </Link>
            <Link href="/workers" className="block">
              <StatTile label="Worker Queue" value={workersResult ? String(workersResult.load_balancer.queue_depth) : "—"} tone={workersResult?.load_balancer.overflowing ? "bad" : "good"} />
            </Link>
            <Link href="/payments" className="block">
              <StatTile label="Payments Collected" value={paymentsResult ? `₹${paymentsResult.total_paid_inr.toLocaleString("en-IN")}` : "—"} tone={paymentsResult?.total_paid_inr ? "good" : "neutral"} hint={paymentsResult ? "Verified stored records" : "Payment API unavailable"} />
            </Link>
            <Link href="/security" className="block">
              <StatTile label="Security Score" value={securityResult?.latest_report ? `${securityResult.latest_report.score}/100` : "—"} hint={securityResult?.latest_report ? `Stored scan: ${securityResult.latest_report.created_at}` : "No stored scan"}
                         tone={securityResult?.latest_report ? (securityResult.latest_report.score >= 70 ? "good" : "bad") : "neutral"} />
            </Link>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Founder Tasks, Projects &amp; OS — complete ledger"
          subtitle={`${allInitiatives.length} imported and Mac-native initiatives — real progress from stored milestones`}
          action={
            <Link href="/initiatives" className="text-xs font-mono text-[var(--local)] hover:underline">
              View all →
            </Link>
          }
        />
        <CardBody>
          {allInitiatives.length === 0 ? (
            <EmptyState>No initiatives recorded.</EmptyState>
          ) : (
            <div className="space-y-3">
              {allInitiatives.map((init) => (
                <Link key={init.id} href="/initiatives" className="block">
                  <div className="flex flex-col gap-1 text-sm mb-1 sm:flex-row sm:items-center sm:justify-between">
                    <span className="text-[var(--ink)] min-w-0">
                      {initiativeLabel(init.track, init.seq)} — {init.title}
                    </span>
                    <span className="flex items-center gap-2 shrink-0">
                      <Badge tone={init.status === "running" ? "good" : init.status === "paused" ? "warn" : "neutral"}>
                        {init.status}
                      </Badge>
                      <span className="font-mono-num text-[var(--muted-foreground)]">
                        {init.percent_complete}% ({init.milestone_done}/{init.milestone_total})
                      </span>
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-[var(--surface-2)] overflow-hidden">
                    <div
                      className="h-full rounded-full bg-[var(--local)]"
                      style={{ width: `${init.percent_complete}%` }}
                    />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Recent Task Records" subtitle="Most recent 15 stored records; timestamps show freshness" />
        <CardBody className="p-0">
          {overview.recent_tasks.length === 0 ? (
            <EmptyState>No tasks yet. Run one from the CLI to see it here.</EmptyState>
          ) : (
            <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--muted-foreground)] border-b border-[var(--border)]">
                  <th className="px-5 py-2 font-medium">ID</th>
                  <th className="px-5 py-2 font-medium">Agent</th>
                  <th className="px-5 py-2 font-medium">Business</th>
                  <th className="px-5 py-2 font-medium">Status</th>
                  <th className="px-5 py-2 font-medium">Risk</th>
                  <th className="px-5 py-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {overview.recent_tasks.map((t) => (
                  <tr key={t.id} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-5 py-2 font-mono-num text-[var(--muted-foreground)]">#{t.id}</td>
                    <td className="px-5 py-2">{t.agent_id}</td>
                    <td className="px-5 py-2 text-[var(--muted-foreground)]">{t.business_id ?? "—"}</td>
                    <td className="px-5 py-2">
                      <Badge tone={t.status === "done" ? "good" : t.status === "failed" ? "bad" : "warn"}>{t.status}</Badge>
                    </td>
                    <td className="px-5 py-2">
                      <Badge tone={t.risk_level === "critical" ? "bad" : "neutral"}>{t.risk_level}</Badge>
                    </td>
                    <td className="px-5 py-2 text-[var(--muted-foreground)] font-mono-num">{t.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Businesses" />
        <CardBody className="flex flex-wrap gap-2">
          {overview.businesses.map((b) => (
            <span key={b.id} className="text-sm rounded-md border border-[var(--border)] px-3 py-1">
              #{b.id} {b.name}
            </span>
          ))}
        </CardBody>
      </Card>
    </div>
  );
}
