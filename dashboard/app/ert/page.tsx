import { getIncidents, getGovernorStatus, getCeoHealth } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

const SEVERITY_TONE: Record<string, "good" | "warn" | "bad" | "neutral"> = {
  P0: "bad", P1: "bad", P2: "warn", P3: "neutral", P4: "neutral",
};
const STATUS_TONE: Record<string, "good" | "warn" | "bad" | "neutral"> = {
  NEW: "neutral", ACKNOWLEDGED: "warn", INVESTIGATING: "warn", FIXING: "warn",
  VERIFYING: "warn", READY_TO_DEPLOY: "warn", RESOLVED: "good", CLOSED: "good",
};
const OPEN_STATUSES = ["NEW", "ACKNOWLEDGED", "INVESTIGATING", "FIXING", "VERIFYING", "READY_TO_DEPLOY"];

function fmtDuration(seconds: number | null) {
  if (seconds === null) return "—";
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m}m`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

export default async function ErtCommandCenterPage() {
  const [{ incidents, mttr_seconds, open_count, critical_count }, governor, ceoHealth] = await Promise.all([
    getIncidents(undefined, undefined, 100), getGovernorStatus(), getCeoHealth(),
  ]);

  const ownerCounts = incidents
    .filter((i) => OPEN_STATUSES.includes(i.status))
    .reduce<Record<string, number>>((acc, i) => { acc[i.owner] = (acc[i.owner] || 0) + 1; return acc; }, {});

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">ERT Command Center</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Emergency Response Team — real incidents, real state machine, real ownership assignment (with backup +
            escalation), real MTTR. Automatic detection reuses Sentinel/Security/payment checks already built
            elsewhere — not a second set of thresholds.
          </p>
        </div>
        <AutoRefresh intervalSeconds={20} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Open Incidents" value={String(open_count)} tone={open_count ? "warn" : "good"} />
        <StatTile label="Critical (P0, open)" value={String(critical_count)} tone={critical_count ? "bad" : "good"} />
        <StatTile label="MTTR" value={fmtDuration(mttr_seconds)} hint="last 30 days" />
        <StatTile label="Total Tracked" value={String(incidents.length)} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatTile label="Governor" value={governor.status} tone={governor.status === "operational" ? "good" : "bad"} />
        <StatTile label="CEO Health" value={ceoHealth.status} tone={ceoHealth.status === "healthy" ? "good" : ceoHealth.status === "degraded" ? "warn" : "bad"} />
        <StatTile label="Failover Events (24h)" value={String(governor.failover_event_count_24h)} tone={governor.failover_event_count_24h ? "warn" : "good"} />
        {Object.entries(governor.subsystems).slice(0, 2).map(([name, s]) => (
          <StatTile key={name} label={name.replace("_", " ")} value={s.ok ? "OK" : "DOWN"} tone={s.ok ? "good" : "bad"} />
        ))}
      </div>

      <Card>
        <CardHeader title="Owner Queue" subtitle="Open incidents per owner" />
        <CardBody>
          {Object.keys(ownerCounts).length === 0 ? (
            <EmptyState>No open incidents — every owner queue is empty.</EmptyState>
          ) : (
            <div className="flex flex-wrap gap-3">
              {Object.entries(ownerCounts).map(([owner, count]) => (
                <div key={owner} className="flex items-center gap-2 rounded-lg border border-[var(--border)] px-3 py-2 text-xs">
                  <span className="capitalize">{owner.replace(/_/g, " ")}</span>
                  <Badge tone={count >= 3 ? "warn" : "neutral"}>{count}</Badge>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Incidents" subtitle={`${incidents.length} tracked`} />
        <CardBody className="p-0">
          {incidents.length === 0 ? (
            <EmptyState>
              No incidents yet. Run <code>python3 -m orchestrator.cli --incident-sweep</code> or file one manually
              with <code>--incident-create website_down --description &quot;...&quot;</code>
            </EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {incidents.map((inc) => (
                <div key={inc.id} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium">{inc.incident_number} · {inc.incident_type.replace(/_/g, " ")}</span>
                    <div className="flex items-center gap-2">
                      <Badge tone={SEVERITY_TONE[inc.severity] ?? "neutral"}>{inc.severity}</Badge>
                      <Badge tone={STATUS_TONE[inc.status] ?? "neutral"}>{inc.status}</Badge>
                    </div>
                  </div>
                  <div className="mt-1.5 flex items-center gap-4 text-xs text-[var(--muted-foreground)]">
                    <span>owner: {inc.owner.replace(/_/g, " ")}</span>
                    <span>support: {inc.support_team.join(", ") || "—"}</span>
                    <span>detected by: {inc.detected_by}</span>
                    <span className="font-mono-num">{inc.created_at}</span>
                  </div>
                  <p className="mt-1.5 text-xs text-[var(--muted-foreground)] max-w-[70ch]">{inc.description}</p>
                  {inc.root_cause && (
                    <p className="mt-1 text-xs text-[var(--muted-foreground)]"><span className="font-medium">Root cause:</span> {inc.root_cause}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
