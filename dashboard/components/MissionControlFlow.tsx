"use client";

import { useMemo, useState, useEffect, useRef } from "react";
import {
  ReactFlow, Background, BackgroundVariant, Handle, Position,
  type Node, type Edge, type NodeProps, BaseEdge, getStraightPath, type EdgeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { motion } from "framer-motion";
import type { Worker, LoadBalancerStatus, FullTask } from "@/lib/api";
import { PERSONA_NAME, PERSONA_FACE, type AgentNode } from "@/lib/systemStatus";
import { AutoRefresh } from "@/components/AutoRefresh";
import { MatrixRain } from "@/components/AmbientEffects";

export type StatusData = {
  nodes: AgentNode[];
  workers: Worker[];
  loadBalancer: LoadBalancerStatus;
  ceoHealth: { status: string; failure_count: number };
  sentinelOk: boolean;
  recentActivity: FullTask[];
  kpis: {
    totalAgents: number;
    activeAgents: number;
    missionsPerMinute: number;
    successRatePercent: number | null;
    bottleneckCount: number;
  };
};

const GLOW: Record<string, string> = {
  cyan: "#22d3ee", violet: "#a78bfa", amber: "#fbbf24", rose: "#fb7185", emerald: "#34d399", slate: "#94a3b8",
};

// Top KPI row (Executive Neural Network spec §7) -- five compact real-data
// tiles, no fabricated trend arrows since there's no stored KPI history to
// derive a real delta from yet.
function KpiPill({ label, value, tone = "slate" }: { label: string; value: string; tone?: keyof typeof GLOW }) {
  return (
    <div
      className="rounded-lg border px-3 py-1.5 backdrop-blur-sm"
      style={{ borderColor: `${GLOW[tone]}33`, background: "rgba(6,9,11,0.65)" }}
    >
      <div className="text-[9px] uppercase tracking-[0.14em] text-slate-500">{label}</div>
      <div className="text-base font-semibold font-mono tabular-nums mt-0.5" style={{ color: GLOW[tone] }}>{value}</div>
    </div>
  );
}

// Deterministic per-node "randomness" -- same label always produces the
// same float duration/delay/amplitude, so the buoy motion doesn't jump or
// resync every ~3s when status polling re-renders the graph. A real RNG
// (Math.random) would reseed every render and look like jitter, not float.
function seedFrom(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h;
}

// Real elapsed time since a real created_at timestamp -- not a fabricated
// "duration" (tasks don't store a completion time, see systemStatus.ts).
function timeAgo(iso: string): string {
  const t = new Date(iso.includes("Z") ? iso : iso + "Z").getTime();
  const seconds = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  return `${Math.floor(seconds / 86400)}d`;
}

const ACTIVITY_STATUS_TONE: Record<string, string> = {
  done: "#34d399", running: "#22d3ee", pending: "#94a3b8", failed: "#fb7185",
};

// --- Custom node: a glowing glass orb, pulses when recently active ---
function OrbNode({ data }: NodeProps) {
  const d = data as unknown as {
    label: string; sublabel: string; color: string; size: "xl" | "lg" | "md" | "sm" | "xs"; active: boolean; face?: string;
  };
  const glow = GLOW[d.color] || GLOW.slate;
  // "xs" is for larger rosters (see ORB_SIZE_TIERS in MissionControlFlow
  // below) -- past ~24 nodes on the ring, "sm" orbs pitch out wider than a
  // laptop screen can show even at max zoom-out. Bumped from 54 -> 66 --
  // still visibly the "small" tier next to sm/md/lg/xl, just not so small
  // the label crowds out the orb itself.
  const dims = { xl: 150, lg: 118, md: 96, sm: 78, xs: 66 }[d.size];
  const fontSize = { xl: 18, lg: 15, md: 12.5, sm: 11, xs: 9.5 }[d.size];

  // "Floating on water" -- every orb bobs gently in place, each on its own
  // phase/period/amplitude so a full ring of them doesn't move in unison
  // (that would read as a pulse, not water). This only animates an inner
  // wrapper, not the outer node root the Handles live on, so the edge
  // endpoints stay put -- like a buoy bobbing on a fixed mooring line
  // instead of the whole line swinging.
  const seed = seedFrom(d.label + d.sublabel);
  const floatDuration = 2.8 + (seed % 140) / 100; // 2.8s - 4.2s
  const floatDelay = (seed % 200) / 100; // 0s - 2s
  const floatAmp = 4 + (seed % 4); // 4px - 7px vertical
  const swayAmp = 2 + (seed % 3); // 2px - 4px horizontal

  return (
    <motion.div
      initial={{ scale: 0.85, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.5 }}
      style={{ width: dims, height: dims }}
      className="relative flex items-center justify-center rounded-full"
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
      <motion.div
        className="absolute inset-0"
        animate={{ y: [0, -floatAmp, 0, floatAmp * 0.5, 0], x: [0, swayAmp, 0, -swayAmp * 0.6, 0] }}
        transition={{ duration: floatDuration, delay: floatDelay, repeat: Infinity, ease: "easeInOut" }}
      >
        {/* Outer soft halo -- a second, wider glow layer behind everything,
            always on (not just when active) so idle nodes still read as neon,
            not flat dark circles. */}
        <div
          className="absolute rounded-full"
          style={{
            inset: -14,
            background: `radial-gradient(circle, ${glow}26 0%, transparent 70%)`,
            filter: "blur(2px)",
          }}
        />
        {d.active && (
          <motion.div
            className="absolute inset-0 rounded-full"
            style={{ boxShadow: `0 0 0 2px ${glow}77` }}
            animate={{ scale: [1, 1.4, 1], opacity: [0.7, 0, 0.7] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
        {/* Flowing neon ring -- a bright arc that orbits the rim, active
            nodes only, so "who's active" reads at a glance from the ring
            animating, not just the label color. A conic-gradient wedge
            masked down to a thin annulus (mask carves out everything but
            a ring at the very edge), then spun with a CSS animation. */}
        {d.active && (
          <div
            className="absolute rounded-full pointer-events-none"
            style={{
              inset: -8,
              background: `conic-gradient(from 0deg, transparent 0deg, ${glow} 55deg, transparent 120deg, transparent 360deg)`,
              WebkitMaskImage: "radial-gradient(farthest-side, transparent calc(100% - 8px), #000 calc(100% - 8px))",
              maskImage: "radial-gradient(farthest-side, transparent calc(100% - 8px), #000 calc(100% - 8px))",
              filter: `drop-shadow(0 0 10px ${glow})`,
              animation: "neonOrbit 2.6s linear infinite",
            }}
          />
        )}
        <div
          className="absolute inset-0 rounded-full backdrop-blur-md"
          style={{
            background: `radial-gradient(circle at 35% 30%, ${glow}44, rgba(8,10,16,0.85) 70%)`,
            border: `3px solid ${glow}aa`,
            boxShadow: `0 0 42px ${glow}77, 0 0 84px ${glow}33, inset 0 0 30px ${glow}38`,
          }}
        />
        <div className="relative z-10 flex flex-col items-center text-center px-1.5 select-none">
          {d.face && <span style={{ fontSize: fontSize + 6, lineHeight: 1, marginBottom: 2 }}>{d.face}</span>}
          <span className="font-semibold leading-tight" style={{ fontSize, color: "#f8fafc" }}>{d.label}</span>
          {d.sublabel && (
            <span className="mt-1 leading-tight font-mono" style={{ fontSize: fontSize - 3.5, color: glow }}>{d.sublabel}</span>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}

// --- Squad header: plain text, marks each cluster in the org tree ---
function SquadLabelNode({ data }: NodeProps) {
  const d = data as unknown as { label: string };
  return (
    <div
      style={{ pointerEvents: "none", width: 220 }}
      className="text-center font-mono text-[12px] uppercase tracking-[0.2em] text-slate-400 select-none"
    >
      {d.label}
    </div>
  );
}

// --- Custom edge: flowing neon energy line, PLUS real traveling packets on
// active connections -- the dashed line says "this connection is active,"
// the moving dot says "here's the direction work is actually flowing,"
// hub -> agent. Two different questions, both real: who's working, and
// which way the work is moving. ---
function FlowEdge({ sourceX, sourceY, targetX, targetY, data }: EdgeProps) {
  const d = data as unknown as { color: string; active: boolean } | undefined;
  const glow = GLOW[d?.color || "slate"] || GLOW.slate;
  const [path] = getStraightPath({ sourceX, sourceY, targetX, targetY });
  const motionPath = `M${sourceX},${sourceY} L${targetX},${targetY}`;

  return (
    <>
      <BaseEdge path={path} style={{ stroke: `${glow}66`, strokeWidth: 6 }} />
      {d?.active && (
        <>
          <path
            d={path}
            fill="none"
            stroke={glow}
            strokeWidth={7.5}
            strokeDasharray="10 12"
            strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 12px ${glow})` }}
          >
            <animate attributeName="stroke-dashoffset" from="44" to="0" dur="1.1s" repeatCount="indefinite" />
          </path>
          {[0, 0.5].map((offset) => (
            <circle key={offset} r="7.5" fill={glow} style={{ filter: `drop-shadow(0 0 12px ${glow})` }}>
              <animateMotion
                dur="1.6s"
                begin={`${offset * 1.6}s`}
                repeatCount="indefinite"
                path={motionPath}
                keyPoints="0;1"
                keyTimes="0;1"
              />
            </circle>
          ))}
        </>
      )}
    </>
  );
}

// --- Option C: a rotating radar sweep + ripple rings, both centered on the
// founder node. Lives INSIDE React Flow's own node space (not a plain
// absolutely-positioned div over the container) so it pans/zooms/fits in
// lockstep with the rest of the graph instead of drifting independently of it. ---
function RadarNode({ data }: NodeProps) {
  const d = data as unknown as { size: number };
  return (
    <div style={{ width: d.size, height: d.size, pointerEvents: "none", position: "relative" }}>
      <div
        className="absolute inset-0 rounded-full"
        style={{
          // Cyan, not violet -- was reading as the "large purple gradient"
          // the founder kept flagging across reference-image comparisons
          // tonight. Matches the ripple rings below and the spec's own
          // color language (cyan = live info flow), restrained at low alpha.
          background: "conic-gradient(from 0deg, transparent 0deg, rgba(34,211,238,0.3) 14deg, transparent 70deg)",
          animation: "radarSpin 5s linear infinite",
          mixBlendMode: "screen",
        }}
      />
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="absolute rounded-full"
          style={{
            left: "50%", top: "50%", width: 24, height: 24, marginLeft: -12, marginTop: -12,
            border: "1px solid rgba(34,211,238,0.55)",
            animation: `radarRipple 3.2s ease-out ${i * 1.05}s infinite`,
          }}
        />
      ))}
    </div>
  );
}

const nodeTypes = { orb: OrbNode, radar: RadarNode, label: SquadLabelNode };
const edgeTypes = { flow: FlowEdge };

type BrandProps = { eyebrow?: string; title?: string; backLabel?: string; backHref?: string };

// Org-tree squad order, left to right -- matches the founder's own squad
// naming (agents/*.yaml `squad:` field, the real source of truth). Any
// squad not in this list still renders, just appended after these three,
// so a new squad added later doesn't silently vanish from the chart.
const SQUAD_ORDER = ["Front End Design", "GStack", "Get Shit Done"];

export default function MissionControlFlow({ status, activityWindowMinutes, brand, variant = "fullscreen" }: { status: StatusData; activityWindowMinutes: number; brand?: BrandProps; variant?: "fullscreen" | "panel" }) {
  const eyebrow = brand?.eyebrow ?? "GVC OS · Mission Control";
  const title = brand?.title ?? "Living System View";
  const backLabel = brand?.backLabel ?? "← Executive Dashboard";
  const backHref = brand?.backHref ?? "/";
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const { nodes, edges } = useMemo(() => {
    const label = (a: AgentNode) => PERSONA_NAME[a.id] ?? a.name.replace(/^Shakthi\s+/, "");
    const face = (a: AgentNode) => PERSONA_FACE[a.id];

    const paAgent = status.nodes.find((a) => a.id === "pa_angella");
    const ceoAgent = status.nodes.find((a) => a.id === "ceo");
    const managerAgent = status.nodes.find((a) => a.id === "manager");
    const leafAgents = status.nodes.filter((a) => a.id !== "ceo" && a.id !== "manager" && a.id !== "pa_angella");

    // Group every remaining real agent by its real squad -- all 17 of the
    // team render, not a hand-picked subset. An agent with no squad yet
    // still shows up, under "Unassigned", rather than disappearing.
    const bySquad = new Map<string, AgentNode[]>();
    for (const a of leafAgents) {
      const key = a.squad || "Unassigned";
      if (!bySquad.has(key)) bySquad.set(key, []);
      bySquad.get(key)!.push(a);
    }
    const squadKeys = [
      ...SQUAD_ORDER.filter((s) => bySquad.has(s)),
      ...[...bySquad.keys()].filter((s) => !SQUAD_ORDER.includes(s)),
    ];

    // Radial hub-and-spoke layout: Founder/Angella/CEO/Manager stack at
    // the true center, real squads arranged as clusters radiating around
    // it at even angles (Executive Neural Network reference, 2026-09-01),
    // each squad's own members arranged in a small arc around their
    // cluster's own angular position. Gaps still scale off orb size, not
    // fixed pixels -- fitView rescales the whole diagram, so only a
    // ratio-to-orb-size survives that rescale, same lesson as the earlier
    // rectangular layout.
    const N = Math.max(leafAgents.length, 1);
    const leafSize: "sm" | "xs" = N > 24 ? "xs" : "sm";
    const leafOrbPx = leafSize === "xs" ? 66 : 78;
    const numSquads = Math.max(squadKeys.length, 1);

    const nodes: Node[] = [];
    const edges: Edge[] = [];

    const cx = 0, cy = 0;
    const sizePx: Record<"xl" | "lg" | "md", number> = { xl: 150, lg: 118, md: 96 };
    // Cluster ring: how far each squad's center sits from the hub. Scales
    // with squad count so more squads don't overlap each other.
    const CLUSTER_RADIUS = leafOrbPx * (3.4 + numSquads * 0.35);
    // Member ring: how far a squad's own agents sit from THEIR squad's
    // angular position, arranged as a small arc facing outward.
    const MEMBER_RADIUS = leafOrbPx * 1.9;

    const angleStep = (2 * Math.PI) / numSquads;
    // Offset by half a step so squads land diagonally (NE/SE/SW/NW for 4
    // squads), never straight up (collides with the fixed header overlay)
    // or straight down (collides with the hub stack's own vertical line,
    // which is what put "Get Shit Done" right on top of Duke before).
    const startAngle = -Math.PI / 2 + angleStep / 2;

    const hubStack: { id: string; label: string; face?: string; sublabel: string; color: string; size: "xl" | "lg" | "md"; active: boolean }[] = [
      { id: "founder", label: "FOUNDER", sublabel: "", color: "cyan", size: "xl", active: true },
    ];
    if (paAgent) hubStack.push({ id: "pa_angella", label: PERSONA_NAME.pa_angella, face: PERSONA_FACE.pa_angella, sublabel: paAgent.sublabel, color: paAgent.color, size: "lg", active: paAgent.active });
    if (ceoAgent) hubStack.push({ id: "ceo", label: label(ceoAgent), face: face(ceoAgent), sublabel: ceoAgent.sublabel, color: ceoAgent.color, size: "lg", active: ceoAgent.active });
    if (managerAgent) hubStack.push({ id: "manager", label: label(managerAgent), face: face(managerAgent), sublabel: managerAgent.sublabel, color: managerAgent.color, size: "md", active: managerAgent.active });

    // Hub stack sits as a tight vertical column right at the true center
    // (matches the reference's "Mission Orchestrator" hub) -- Founder on
    // top, the real relay chain descending toward the center point that
    // every squad radiates out from.
    let stackTop = cy - (hubStack.reduce((sum, n) => sum + sizePx[n.size], 0) + (hubStack.length - 1) * leafOrbPx * 0.5) / 2;
    let hubId = hubStack[0].id;
    hubStack.forEach((n, i) => {
      const h = sizePx[n.size];
      nodes.push({
        id: n.id, type: "orb", position: { x: cx - h / 2, y: stackTop }, draggable: false,
        data: { label: n.label, face: n.face, sublabel: n.sublabel, color: n.color, size: n.size, active: n.active },
      });
      if (i > 0) {
        edges.push({ id: `e-${hubStack[i - 1].id}-${n.id}`, source: hubStack[i - 1].id, target: n.id, type: "flow", data: { color: n.color, active: true } });
      }
      stackTop += h + leafOrbPx * 0.5;
      hubId = n.id;
    });

    squadKeys.forEach((squad, si) => {
      const members = bySquad.get(squad)!;
      const angle = startAngle + si * angleStep;
      const clusterX = cx + CLUSTER_RADIUS * Math.cos(angle);
      const clusterY = cy + CLUSTER_RADIUS * Math.sin(angle);

      nodes.push({
        id: `label-${squad}`, type: "label", position: { x: clusterX - 110, y: clusterY - leafOrbPx * 1.5 },
        draggable: false, selectable: false, data: { label: squad },
      });
      edges.push({ id: `e-${hubId}-cluster-${squad}`, source: hubId, target: members[0]?.id ?? `label-${squad}`, type: "flow", data: { color: members[0]?.color ?? "slate", active: members.some((m) => m.active) } });

      // Members fan out in a small arc around their own cluster position,
      // facing outward (away from the hub) -- a real mini fan, not a
      // straight line, so a squad of 6-8 agents still reads as one
      // cluster instead of a spoke.
      const arcSpan = Math.min(angleStep * 0.9, Math.PI / 2.2);
      members.forEach((m, mi) => {
        const memberAngle = angle - arcSpan / 2 + (members.length > 1 ? (arcSpan * mi) / (members.length - 1) : arcSpan / 2);
        const mx = clusterX + MEMBER_RADIUS * Math.cos(memberAngle);
        const my = clusterY + MEMBER_RADIUS * Math.sin(memberAngle);
        nodes.push({
          id: m.id, type: "orb", position: { x: mx, y: my }, draggable: false,
          data: { label: label(m), face: face(m), sublabel: m.sublabel, color: m.color, size: leafSize, active: m.active },
        });
        if (mi > 0) {
          edges.push({ id: `e-${members[0].id}-${m.id}`, source: members[0].id, target: m.id, type: "flow", data: { color: m.color, active: m.active } });
        } else {
          edges.push({ id: `e-${hubId}-${m.id}`, source: hubId, target: m.id, type: "flow", data: { color: m.color, active: m.active } });
        }
      });
    });

    // Worker pools -- placed as an outer ring beyond the squad clusters,
    // each linked to one real agent per squad that actually feeds it
    // (worker_registry.TASK_KINDS' real rapid/engineering/infra split).
    const workerTypes = ["rapid", "engineering", "infra"];
    const servicedBy: Record<string, string[]> = {
      rapid: ["chrome_developer", "finance"], engineering: ["bug_fixer", "website_builder"], infra: ["security", "qa"],
    };
    const OUTER_RADIUS = CLUSTER_RADIUS + MEMBER_RADIUS * 1.6;
    workerTypes.forEach((wt, i) => {
      const angle = Math.PI / 2 + (i - 1) * 0.5; // clustered toward the bottom, out of the squads' way
      const x = cx + OUTER_RADIUS * Math.cos(angle);
      const y = cy + OUTER_RADIUS * Math.sin(angle);
      const busy = status.workers.filter((w) => w.worker_type === wt && w.status === "busy").length;
      const total = status.workers.filter((w) => w.worker_type === wt).length;
      nodes.push({
        id: `worker-${wt}`, type: "orb", position: { x, y }, draggable: false,
        data: { label: `${wt.toUpperCase()}\nPOOL`, sublabel: `${busy}/${total} busy`, color: "slate", size: leafSize, active: busy > 0 },
      });
      servicedBy[wt].forEach((agentId) => {
        if (leafAgents.some((a) => a.id === agentId)) {
          edges.push({ id: `e-${wt}-${agentId}`, source: agentId, target: `worker-${wt}`, type: "flow", data: { color: "slate", active: busy > 0 } });
        }
      });
    });

    const radarSize = (CLUSTER_RADIUS + MEMBER_RADIUS) * 2.6;
    nodes.push({
      id: "radar-bg", type: "radar",
      position: { x: cx - radarSize / 2, y: cy - radarSize / 2 },
      draggable: false, selectable: false, zIndex: -1,
      data: { size: radarSize },
    });

    return { nodes, edges };
  }, [status]);

  return (
    <div
      className={`${variant === "fullscreen" ? "fixed inset-0" : "relative w-full h-full"} overflow-hidden`}
      style={{ background: variant === "fullscreen" ? "#020303" : "transparent" }}
    >
      <style>{`
        @keyframes radarSpin { to { transform: rotate(360deg); } }
        @keyframes radarRipple {
          0%   { transform: scale(1);   opacity: 0.65; }
          100% { transform: scale(11);  opacity: 0; }
        }
        @keyframes neonOrbit { to { transform: rotate(360deg); } }
      `}</style>

      {/* "panel" variant (the /concept3 composite) shares the one page-level
          matrix rain instead of owning a second canvas -- avoids a duplicate
          RAF loop and the layered-background occlusion bug found tonight. */}
      {mounted && variant === "fullscreen" && <MatrixRain />}

      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-8 py-5">
        <div>
          <div className="text-[11px] uppercase tracking-[0.25em] text-cyan-400/80 font-mono">{eyebrow}</div>
          <div className="text-xl font-semibold text-slate-100 mt-0.5">{title}</div>
        </div>
        <div className="flex items-center gap-3">
          <AutoRefresh intervalSeconds={1} />
          {backLabel && (
            <a href={backHref} className="text-xs font-mono text-slate-400 hover:text-slate-100 border border-slate-700 rounded-full px-3 py-1.5">
              {backLabel}
            </a>
          )}
        </div>
      </div>

      <div className="absolute top-16 left-8 right-8 z-10 grid grid-cols-5 gap-2 max-w-3xl">
        <KpiPill label="Total Agents" value={String(status.kpis.totalAgents)} />
        <KpiPill label="Active Agents" value={String(status.kpis.activeAgents)} tone="emerald" />
        <KpiPill label="Missions / Min" value={status.kpis.missionsPerMinute.toFixed(1)} tone="cyan" />
        <KpiPill
          label="Success Rate"
          value={status.kpis.successRatePercent !== null ? `${status.kpis.successRatePercent}%` : "N/A"}
          tone={status.kpis.successRatePercent === null ? "slate" : status.kpis.successRatePercent >= 90 ? "emerald" : "amber"}
        />
        <KpiPill label="Bottlenecks" value={String(status.kpis.bottleneckCount)} tone={status.kpis.bottleneckCount > 0 ? "rose" : "emerald"} />
      </div>

      {mounted && (
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={{
            padding: 0.16,
            // Real bug just found: the giant radar-sweep node's bounding
            // box was included in fitView's calculation, so React Flow
            // zoomed out to fit a mostly-empty 2000px+ circle instead of
            // the actual tree -- that's what was making everything look
            // small. Fit to the real content nodes only; the radar still
            // renders (zIndex -1, behind everything), it just doesn't
            // dictate the zoom level anymore.
            nodes: nodes.filter((n) => n.type !== "radar").map((n) => ({ id: n.id })),
          }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          // React Flow's default minZoom (0.5) is the actual reason a big
          // roster went off-screen -- fitView can request whatever zoom it
          // needs, but couldn't go below 0.5x, so once the diagram grew
          // past 2x the viewport it just clipped instead of shrinking.
          // 0.05 lets a full 50-node ring shrink to fit a laptop screen.
          minZoom={0.05}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} gap={28} size={1} color="#1e293b" />
        </ReactFlow>
      )}

      {/* Live Activity Stream (spec §11) -- real /api/tasks rows, newest
          first. No fabricated DURATION column (see systemStatus.ts note);
          shows real elapsed time since created_at instead. */}
      <div
        className="absolute bottom-14 left-8 z-10 w-96 max-h-52 overflow-y-auto rounded-lg border backdrop-blur-sm"
        style={{ borderColor: "rgba(255,255,255,0.08)", background: "rgba(6,9,11,0.75)" }}
      >
        <div className="sticky top-0 grid grid-cols-[3rem_5rem_1fr_2.5rem] gap-2 px-3 py-1.5 text-[9px] uppercase tracking-[0.12em] text-slate-500 border-b border-white/5" style={{ background: "rgba(6,9,11,0.92)" }}>
          <span>Time</span><span>Agent</span><span>Action</span><span>Status</span>
        </div>
        {status.recentActivity.length === 0 ? (
          <div className="px-3 py-3 text-[11px] text-slate-500">No real task activity recorded yet.</div>
        ) : (
          status.recentActivity.map((t) => (
            <div key={t.id} className="grid grid-cols-[3rem_5rem_1fr_2.5rem] gap-2 px-3 py-1 text-[10px] font-mono text-slate-300 border-b border-white/5 last:border-0">
              <span className="text-slate-500 tabular-nums">{timeAgo(t.created_at)}</span>
              <span className="truncate" title={t.agent_id}>{PERSONA_NAME[t.agent_id] ?? t.agent_id}</span>
              <span className="truncate" title={t.goal}>{t.goal}</span>
              <span className="font-semibold" style={{ color: ACTIVITY_STATUS_TONE[t.status] ?? "#94a3b8" }}>{t.status}</span>
            </div>
          ))
        )}
      </div>

      <div className="absolute bottom-5 right-8 z-10 flex items-center gap-5 text-[11px] font-mono text-slate-400">
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_#34d399]" /> Healthy</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_6px_#fbbf24]" /> Attention</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-rose-400 shadow-[0_0_6px_#fb7185]" /> Critical</span>
        <span className="text-slate-600">·</span>
        <span>All {status.nodes.length} agents · Pulsing = real activity in the last {activityWindowMinutes} min, per subsystem&apos;s own data (polled, not push)</span>
      </div>
    </div>
  );
}
