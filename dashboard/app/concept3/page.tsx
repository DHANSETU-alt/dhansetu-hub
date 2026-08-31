import { loadSystemStatus, ACTIVITY_WINDOW_MINUTES } from "@/lib/systemStatus";
import MissionControlFlow from "@/components/MissionControlFlow";
import { ExecutivePanel } from "@/components/ExecutivePanel";
import { SHAKTHI_OS_VERSION } from "@/lib/version";

export const dynamic = "force-dynamic";

// The real "Concept 3 — Executive Neural Network" composite view: the
// Living System View graph and the CEO Dashboard shown side by side in
// one screen, matching the founder's reference image structurally. Both
// halves use 100% real data (the same status/decisions/health/governor
// already powering the standalone /mission-control and /ceo pages) --
// nothing here is a new data source, just a new layout combining two
// already-real views. Anything the reference shows with no real backend
// (Business Impact Score, Value Realized, Strategic Approvals $ amounts)
// renders as an honest "NOT CONNECTED" tile in ExecutivePanel, not a
// fabricated number.
export default async function Concept3Page() {
  const status = await loadSystemStatus();

  return (
    // Transparent everywhere -- the one real matrix rain instance already
    // running fixed behind the whole app (app/layout.tsx) shows through
    // this entire page instead of being painted over by a second, occluded
    // copy. Panels use the .glass treatment so text stays readable over it.
    <div className="fixed inset-0 flex flex-col">
      <div className="glass h-8 flex items-center justify-center text-[10px] tracking-[0.14em] text-[var(--muted-foreground)] uppercase border-x-0 border-t-0 rounded-none">
        {SHAKTHI_OS_VERSION.osName} Concept 3 &mdash; Executive Neural Network
        <span className="mx-2 opacity-40">&bull;</span>
        <span className="lowercase italic normal-case tracking-normal">Intelligent. Autonomous. Accountable.</span>
      </div>
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 min-w-0 border-r border-[var(--border)] relative">
          <MissionControlFlow
            status={status}
            activityWindowMinutes={ACTIVITY_WINDOW_MINUTES}
            variant="panel"
            brand={{ eyebrow: "SHAKTHI_OS · LIVE", title: "Living System View", backLabel: "", backHref: "#" }}
          />
        </div>
        <div className="glass w-[380px] shrink-0 border-y-0 border-r-0 rounded-none overflow-y-auto">
          <ExecutivePanel />
        </div>
      </div>
    </div>
  );
}
