import { getDecisions, getCeoHealth, getGovernorStatus } from "@/lib/api";
import { SHAKTHI_OS_VERSION } from "@/lib/version";

const HEALTH_DOT = { healthy: "#34d399", degraded: "#fbbf24", down: "#fb7185", unknown: "#94a3b8" } as const;

function KpiTile({ label, value, tone = "cyan" }: { label: string; value: string; tone?: "cyan" | "emerald" | "amber" | "violet" }) {
  const ring = { cyan: "#22d3ee", emerald: "#34d399", amber: "#fbbf24", violet: "#a78bfa" }[tone];
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
      <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted-foreground)]">{label}</div>
      <div className="text-2xl font-semibold mt-1 font-mono-num" style={{ color: ring }}>{value}</div>
    </div>
  );
}

function NotConnected({ label }: { label: string }) {
  return (
    <div className="rounded-xl border border-dashed border-[var(--border)] px-4 py-3 text-[11px] text-[var(--muted-foreground)]">
      <div className="uppercase tracking-[0.14em] mb-1">{label}</div>
      <span className="text-[var(--muted-foreground)]/70">NOT CONNECTED — no real backend for this yet</span>
    </div>
  );
}

// Real, honest right-hand executive panel for the two-panel "Concept 3"
// composite view (see SHAKTHI_OS_3.1_NEURAL_NETWORK_UI_ROADMAP.md).
// Only shows real data (real decisions, real CEO health, real governor
// status) -- anything the reference mockup shows that has no real backend
// (Business Impact Score, Value Realized, Strategic Approvals $ amounts,
// Failure Readiness RTO/RPO) renders as an honest "NOT CONNECTED" tile
// instead of a fabricated number, per the founder's own "no fake success"
// rule.
export async function ExecutivePanel() {
  const [{ decisions }, health, governor] = await Promise.all([getDecisions(10), getCeoHealth(), getGovernorStatus()]);
  const approved = decisions.filter((d) => d.status === "approved").length;
  const rejected = decisions.filter((d) => d.status === "rejected").length;
  const revise = decisions.filter((d) => d.status === "revise").length;

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold flex items-center gap-1.5">
            {SHAKTHI_OS_VERSION.osName}
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><path d="M20 6L9 17l-5-5" stroke="#34d399" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </div>
          <div className="text-xs text-[var(--muted-foreground)]">CEO Dashboard</div>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded-full border border-[var(--border)] text-[var(--muted-foreground)]">LIVE</span>
      </div>

      <div className="p-4 space-y-4 overflow-y-auto flex-1">
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted-foreground)] mb-2">Decisions (real, last 10)</div>
          <div className="grid grid-cols-3 gap-2">
            <KpiTile label="Approved" value={String(approved)} tone="emerald" />
            <KpiTile label="Revise" value={String(revise)} tone="amber" />
            <KpiTile label="Rejected" value={String(rejected)} tone="violet" />
          </div>
        </div>

        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted-foreground)] mb-2">Health Monitor</div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: HEALTH_DOT[health.status] }} />
              <span className="text-sm font-medium capitalize">{health.status}</span>
              <span className="text-[10px] text-[var(--muted-foreground)] ml-auto">{health.total_tracked} tasks tracked</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div><span className="text-[var(--muted-foreground)]">Failures</span> <b className="font-mono-num">{health.failure_count}</b></div>
              <div><span className="text-[var(--muted-foreground)]">Local fallback</span> <b className="font-mono-num">{health.degraded_count}</b></div>
            </div>
          </div>
        </div>

        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted-foreground)] mb-2">Governor — Zero CEO Dependency</div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium capitalize">{governor.status}</span>
              <span className="text-[10px] text-[var(--muted-foreground)]">{Object.keys(governor.subsystems).length} subsystems</span>
            </div>
            <div className="grid grid-cols-2 gap-1.5">
              {Object.entries(governor.subsystems).map(([name, s]) => (
                <div key={name} className="flex items-center justify-between text-[10px] rounded-md border border-[var(--border)] px-2 py-1">
                  <span className="capitalize truncate">{name.replace(/_/g, " ")}</span>
                  <span style={{ color: s.ok ? "#34d399" : "#fb7185" }}>{s.ok ? "OK" : "DOWN"}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted-foreground)] mb-2">Not Yet Real (honestly, not faked)</div>
          <div className="grid grid-cols-2 gap-2">
            <NotConnected label="Business Impact Score" />
            <NotConnected label="Value Realized" />
            <NotConnected label="Strategic Approvals" />
            <NotConnected label="Failure Readiness" />
          </div>
        </div>

        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted-foreground)] mb-2">Recent Decisions</div>
          <div className="space-y-1.5">
            {decisions.slice(0, 5).map((d) => (
              <div key={d.id} className="rounded-lg border border-[var(--border)] px-3 py-2 text-[11px]">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate">{d.goal}</span>
                  <span
                    className="shrink-0 text-[9px] uppercase px-1.5 py-0.5 rounded-full"
                    style={{
                      color: d.status === "approved" ? "#34d399" : d.status === "rejected" ? "#fb7185" : "#fbbf24",
                      background: d.status === "approved" ? "#34d39922" : d.status === "rejected" ? "#fb718522" : "#fbbf2422",
                    }}
                  >
                    {d.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
