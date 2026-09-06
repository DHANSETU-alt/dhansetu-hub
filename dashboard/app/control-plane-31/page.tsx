import { getV31Missions, getV31WorldModel, getV31Audit, getV31Events, getV31Governance } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

const RISK_TONE: Record<string, "good" | "warn" | "bad"> = {
  LOW: "good", MEDIUM: "warn", HIGH: "bad", CRITICAL: "bad",
};

export default async function ControlPlane31Page() {
  const [missionsRes, worldModelRes, auditRes, eventsRes, governanceRes] = await Promise.all([
    getV31Missions(),
    getV31WorldModel(),
    getV31Audit(),
    getV31Events(50),
    getV31Governance(),
  ]);
  const { missions } = missionsRes;
  const { entities } = worldModelRes;
  const { chain_valid, entries } = auditRes;
  const { events } = eventsRes;
  const { autonomy_levels, truth_states } = governanceRes;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">SHAKTHI_OS 3.1 Control Plane</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Newly merged governance, hash-chained audit, world model, and mission foundation from the 3.1 blueprint. Read-only —
            mission creation and other state-changing actions are gated behind founder approval that isn&apos;t wired up yet.
          </p>
        </div>
        <AutoRefresh intervalSeconds={1} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Audit Chain" value={chain_valid ? "VALID" : "BROKEN"} tone={chain_valid ? "good" : "bad"} />
        <StatTile label="Missions" value={String(missions.length)} />
        <StatTile label="World Model Entities" value={String(entities.length)} />
        <StatTile label="Recent Events" value={String(events.length)} />
      </div>

      <Card>
        <CardHeader title="Missions" subtitle="Angela mission drafts, with governance autonomy level and intake confidence" />
        <CardBody className="p-0">
          {missions.length === 0 ? (
            <EmptyState>No missions drafted yet.</EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {missions.map((m) => (
                <div key={m.mission_id} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium">{m.objective}</span>
                    <div className="flex items-center gap-2">
                      <Badge tone={RISK_TONE[m.risk] ?? "neutral"}>{m.risk}</Badge>
                      <Badge tone="neutral">{m.current_status}</Badge>
                    </div>
                  </div>
                  <div className="mt-1.5 flex items-center gap-4 text-xs text-[var(--muted-foreground)]">
                    <span>{m.department}</span>
                    <span>{m.autonomy_level}</span>
                    <span>confidence {m.confidence.overall}/100</span>
                    <span className="font-mono-num">{m.created_at}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Audit Log" subtitle="Append-only, hash-chained action log" />
        <CardBody className="p-0">
          {entries.length === 0 ? (
            <EmptyState>No audit entries yet.</EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {entries.map((e) => (
                <div key={e.hash} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium">{e.action}</span>
                    <Badge tone="neutral">{e.result}</Badge>
                  </div>
                  <div className="mt-1.5 flex items-center gap-4 text-xs text-[var(--muted-foreground)]">
                    <span>{e.agent}</span>
                    <span>{e.reason}</span>
                    <span className="font-mono-num">{e.timestamp}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="World Model" subtitle="Typed entities in the enterprise knowledge graph" />
        <CardBody className="p-0">
          {entities.length === 0 ? (
            <EmptyState>No entities recorded yet.</EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {entities.map((ent) => (
                <div key={ent.id} className="px-5 py-3 flex items-center justify-between gap-3">
                  <span className="text-sm font-medium">{ent.name}</span>
                  <div className="flex items-center gap-2 text-xs text-[var(--muted-foreground)]">
                    <Badge tone="neutral">{ent.type}</Badge>
                    <span className="font-mono-num">{ent.updated_at}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Governance Framework" subtitle="Autonomy ladder and truth-state lifecycle this package enforces" />
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="text-xs uppercase tracking-wide text-[var(--muted-foreground)] mb-2">Autonomy Levels</div>
              <div className="space-y-1.5">
                {autonomy_levels.map((level) => (
                  <div key={level.name} className="flex items-center justify-between text-sm">
                    <span>{level.name}</span>
                    <span className="font-mono-num text-[var(--muted-foreground)]">{level.value}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-[var(--muted-foreground)] mb-2">Truth States</div>
              <div className="flex flex-wrap gap-1.5">
                {truth_states.map((state) => (
                  <Badge key={state} tone="neutral">{state}</Badge>
                ))}
              </div>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
