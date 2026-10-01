import type { MacRuntime, LinuxRuntime } from "@/lib/api";

// Live topology circuit: Mac (master/host of this dashboard, always
// online while this page rendered) <-> Linux GPU node (reachable field is
// a real SSH sample this same request, never cached) <-> Agent roster
// (a real count from the agents table, not a live per-agent heartbeat --
// this system doesn't have per-agent liveness yet, so we show roster size
// and how many have real recent activity instead of fabricating an
// online/offline dot per agent). Server component: all data is a prop,
// computed once per request by the page, same "no client-side guessing"
// rule as the rest of this dashboard.
//
// Pure SVG + CSS keyframes for the trace animation (stroke-dashoffset
// marching along each path) -- no canvas, no client JS needed, so this
// renders identically on the very first paint instead of popping in.
export function SystemCircuitDiagram({
  macRuntime,
  linuxRuntime,
  agentCount,
  activeAgentCount,
}: {
  macRuntime: MacRuntime | null;
  linuxRuntime: LinuxRuntime | null;
  agentCount: number;
  activeAgentCount: number;
}) {
  // Real bug fixed 2026-09-16: this component assumed it always renders
  // ON the Mac, looking outward at Linux over SSH. Once the same codebase
  // also runs ON the Linux box (the mirror), that SSH call targeted
  // itself -- always "UNREACHABLE" (wrong key path, and SSHing to
  // yourself to ask "am I up" makes no sense anyway). Self-aware fix:
  // when macRuntime.os is "Linux", THIS request's own real sample IS the
  // Linux node (always online, no SSH needed) -- and Mac's status is
  // honestly reported as not-checked-from-here, since no reverse-SSH
  // (Linux -> Mac) capability exists.
  const onLinuxHost = macRuntime?.os === "Linux";
  const macUp = onLinuxHost ? null : !!macRuntime;

  const linuxUp = onLinuxHost ? !!macRuntime : linuxRuntime?.reachable === true;
  const linuxLabel = onLinuxHost
    ? macRuntime
      ? `${macRuntime.hostname} · ${macRuntime.cpu_percent}% CPU (this machine)`
      : "Runtime unavailable"
    : linuxRuntime
      ? linuxRuntime.reachable
        ? `${linuxRuntime.hostname} · ${linuxRuntime.gpu.state === "CONNECTED" ? linuxRuntime.gpu.name : linuxRuntime.gpu.state}`
        : linuxRuntime.error
      : "No sample this request";

  const macLabel = onLinuxHost
    ? "No reverse SSH from Linux -> Mac yet"
    : macRuntime
      ? `${macRuntime.hostname} · ${macRuntime.cpu_percent}% CPU`
      : "Runtime unavailable";

  return (
    <div className="glass hud-card rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-[var(--ink)]">Live System Circuit</h2>
          <p className="text-xs text-[var(--muted-foreground)] mt-0.5">Mac (master) &lt;-&gt; Linux GPU node &lt;-&gt; Agent roster — real connectivity, sampled this request</p>
        </div>
      </div>

      <div className="relative bg-black/40 p-2">
        <style>{`
          @keyframes circuitTraceFlow { to { stroke-dashoffset: -24; } }
          .circuit-trace-live { animation: circuitTraceFlow 1s linear infinite; }
          .circuit-node-glow { filter: drop-shadow(0 0 6px currentColor); }
        `}</style>
        <svg viewBox="0 0 820 300" className="w-full h-auto" role="img" aria-label="Mac, Linux, and agent roster connectivity diagram">
          {/* traces (right-angle PCB-style) */}
          <g fill="none" strokeWidth={2}>
            {/* Mac -> Linux */}
            <path
              d="M 210 90 H 330 V 60 H 590"
              stroke={macUp && linuxUp ? "#22ff88" : "#3a4a44"}
              strokeDasharray={macUp && linuxUp ? "6 6" : undefined}
              className={macUp && linuxUp ? "circuit-trace-live" : undefined}
              opacity={macUp && linuxUp ? 0.9 : 0.4}
            />
            {/* Mac -> Agents */}
            <path
              d="M 210 150 H 300 V 220 H 400"
              stroke={macUp ? "#22ff88" : "#3a4a44"}
              strokeDasharray={macUp ? "6 6" : undefined}
              className={macUp ? "circuit-trace-live" : undefined}
              opacity={macUp ? 0.9 : 0.4}
            />
          </g>

          {/* MAC node -- macUp is null (not false) when this page is being
              served BY the Linux machine itself: honestly "not checked",
              not a fabricated red OFFLINE, since no reverse-SSH exists yet. */}
          <g transform="translate(30,60)" className="circuit-node-glow" style={{ color: macUp === null ? "#ffb347" : macUp ? "#22ff88" : "#ff4d6d" }}>
            <rect width={180} height={90} rx={6} fill="#05130c" stroke="currentColor" strokeWidth={1.5} />
            {Array.from({ length: 6 }).map((_, i) => (
              <rect key={i} x={-4} y={12 + i * 13} width={8} height={4} fill="currentColor" />
            ))}
            <text x={16} y={26} fill="currentColor" fontFamily="monospace" fontSize={14} fontWeight={700}>MAC · MASTER</text>
            <text x={16} y={46} fill="#9fb8ac" fontFamily="monospace" fontSize={11}>{macLabel}</text>
            <text x={16} y={64} fill="currentColor" fontFamily="monospace" fontSize={11} fontWeight={700}>{macUp === null ? "● NOT CHECKED" : macUp ? "● ONLINE" : "● OFFLINE"}</text>
          </g>

          {/* LINUX node */}
          <g transform="translate(590,15)" className="circuit-node-glow" style={{ color: linuxUp ? "#22ff88" : "#ff4d6d" }}>
            <rect width={200} height={90} rx={6} fill="#05130c" stroke="currentColor" strokeWidth={1.5} />
            {Array.from({ length: 6 }).map((_, i) => (
              <rect key={i} x={196} y={12 + i * 13} width={8} height={4} fill="currentColor" />
            ))}
            <text x={16} y={26} fill="currentColor" fontFamily="monospace" fontSize={14} fontWeight={700}>LINUX · GPU</text>
            <text x={16} y={46} fill="#9fb8ac" fontFamily="monospace" fontSize={11}>{linuxLabel.length > 30 ? linuxLabel.slice(0, 30) + "…" : linuxLabel}</text>
            <text x={16} y={64} fill="currentColor" fontFamily="monospace" fontSize={11} fontWeight={700}>{linuxUp ? "● REACHABLE" : "● UNREACHABLE"}</text>
          </g>

          {/* AGENTS node */}
          <g transform="translate(400,190)" className="circuit-node-glow" style={{ color: "#22ff88" }}>
            <rect width={200} height={90} rx={6} fill="#05130c" stroke="currentColor" strokeWidth={1.5} />
            {Array.from({ length: 6 }).map((_, i) => (
              <rect key={i} x={-4} y={12 + i * 13} width={8} height={4} fill="currentColor" />
            ))}
            <text x={16} y={26} fill="currentColor" fontFamily="monospace" fontSize={14} fontWeight={700}>AGENT ROSTER</text>
            <text x={16} y={46} fill="#9fb8ac" fontFamily="monospace" fontSize={11}>{agentCount} defined, {activeAgentCount} active recently</text>
            <text x={16} y={64} fill="currentColor" fontFamily="monospace" fontSize={11} fontWeight={700}>● {agentCount} REGISTERED</text>
          </g>
        </svg>
      </div>
    </div>
  );
}
