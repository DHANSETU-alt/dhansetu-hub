import type { PaAngellaStatus } from "@/lib/api";

// PA Angella's real visual identity in the dashboard chrome -- an abstract
// glyph, not a human figure, matching Mission Control's own convention of
// representing every entity (Founder, CEO, Manager, squads) as a glowing
// node rather than a literal render. See the design brief saved to the
// knowledge base ("PA Angella -- Professional Mascot Design Brief") for
// the full reasoning. status is null when the API couldn't be reached --
// renders a quiet idle state rather than nothing.
export function AngellaPresence({ status }: { status: PaAngellaStatus | null }) {
  const active = status?.active ?? false;

  return (
    <div className="flex items-center gap-2.5 px-4 py-3 border-b border-[var(--border)]">
      <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
        <circle cx="13" cy="13" r="4" fill="#22d3ee" opacity={active ? "0.95" : "0.55"} />
        <circle
          cx="13" cy="13" r="8" fill="none" stroke="#22d3ee" strokeWidth="1"
          opacity={active ? "0.55" : "0.25"}
        >
          {active && (
            <animate attributeName="r" values="7;10;7" dur="2.2s" repeatCount="indefinite" />
          )}
        </circle>
        <circle
          cx="13" cy="13" r="11.5" fill="none" stroke="#22d3ee" strokeWidth="0.75"
          opacity={active ? "0.3" : "0.12"}
        >
          {active && (
            <animate attributeName="opacity" values="0.3;0.05;0.3" dur="2.2s" repeatCount="indefinite" />
          )}
        </circle>
      </svg>
      <div className="min-w-0">
        <div className="text-xs font-medium text-[var(--ink)] leading-tight">PA Angella</div>
        <div className="text-[10px] text-[var(--muted-foreground)] leading-tight mt-0.5">
          {status === null ? "—" : active ? `Active · ${status.recent_task_count} recent` : "Standing by"}
        </div>
      </div>
    </div>
  );
}
