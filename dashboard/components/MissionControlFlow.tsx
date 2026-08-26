"use client";

import { useMemo, useState, useEffect, useRef } from "react";
import {
  ReactFlow, Background, BackgroundVariant, Handle, Position,
  type Node, type Edge, type NodeProps, BaseEdge, getStraightPath, type EdgeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { motion } from "framer-motion";
import type { Worker, LoadBalancerStatus } from "@/lib/api";
import type { AgentNode } from "@/lib/systemStatus";
import { AutoRefresh } from "@/components/AutoRefresh";
import { MatrixRain, FireflySwarm } from "@/components/AmbientEffects";

export type StatusData = {
  nodes: AgentNode[];
  workers: Worker[];
  loadBalancer: LoadBalancerStatus;
  ceoHealth: { status: string; failure_count: number };
  sentinelOk: boolean;
};

const GLOW: Record<string, string> = {
  cyan: "#22d3ee", violet: "#a78bfa", amber: "#fbbf24", rose: "#fb7185", emerald: "#34d399", slate: "#94a3b8",
};

// Deterministic per-node "randomness" -- same label always produces the
// same float duration/delay/amplitude, so the buoy motion doesn't jump or
// resync every ~3s when status polling re-renders the graph. A real RNG
// (Math.random) would reseed every render and look like jitter, not float.
function seedFrom(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h;
}

// --- Custom node: a glowing glass orb, pulses when recently active ---
function OrbNode({ data }: NodeProps) {
  const d = data as unknown as {
    label: string; sublabel: string; color: string; size: "xl" | "lg" | "md" | "sm" | "xs"; active: boolean;
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
          background: "conic-gradient(from 0deg, transparent 0deg, rgba(167,139,250,0.5) 14deg, transparent 70deg)",
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

export default function MissionControlFlow({ status, activityWindowMinutes, brand }: { status: StatusData; activityWindowMinutes: number; brand?: BrandProps }) {
  const eyebrow = brand?.eyebrow ?? "GVC OS · Mission Control";
  const title = brand?.title ?? "Living System View";
  const backLabel = brand?.backLabel ?? "← Executive Dashboard";
  const backHref = brand?.backHref ?? "/";
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const { nodes, edges } = useMemo(() => {
    const label = (a: AgentNode) => a.name.replace(/^Shakthi\s+/, "");

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

    // Rectangular flow layout: Founder / PA Angella / CEO / Manager form a
    // vertical hub stack at top-center, and every squad's members wrap
    // into a clean row/column grid beneath their own squad label -- pure
    // rows and columns, no circular geometry. Same lesson learned from the
    // earlier radial version: gaps are set as MULTIPLES of orb size, not
    // fixed pixels, because fitView rescales the whole diagram to fill the
    // viewport -- a flat pixel gap just gets zoomed out to the same visual
    // density; only a gap-to-orb-size ratio survives that rescale.
    const N = Math.max(leafAgents.length, 1);
    const leafSize: "sm" | "xs" = N > 24 ? "xs" : "sm";
    const leafOrbPx = leafSize === "xs" ? 66 : 78;
    const leafHalf = leafOrbPx / 2;
    const GAP_X = leafOrbPx * 1.9;
    const GAP_Y = leafOrbPx * 2.1;
    const CLUSTER_GAP_X = leafOrbPx * 2.6;
    const ROWS_PER_CLUSTER = 2;

    const nodes: Node[] = [];
    const edges: Edge[] = [];

    // Squad clusters, left to right, each wrapping into ROWS_PER_CLUSTER
    // rows so one large squad doesn't stretch the whole diagram into a
    // single endless row.
    const xForAgent = new Map<string, number>();
    const rowForAgent = new Map<string, number>();
    const clusterRanges: { squad: string; x0: number; x1: number }[] = [];
    let xCursor = 0;
    squadKeys.forEach((squad) => {
      const members = bySquad.get(squad)!;
      const half = Math.ceil(members.length / ROWS_PER_CLUSTER);
      const rows = [members.slice(0, half), members.slice(half)];
      const maxRowLen = Math.max(rows[0].length, rows[1].length, 1);
      const start = xCursor;
      rows.forEach((rowMembers, rowIdx) => {
        rowMembers.forEach((m, colIdx) => {
          xForAgent.set(m.id, xCursor + colIdx * GAP_X);
          rowForAgent.set(m.id, rowIdx);
        });
      });
      xCursor += maxRowLen * GAP_X;
      clusterRanges.push({ squad, x0: start, x1: xCursor - GAP_X });
      xCursor += CLUSTER_GAP_X;
    });
    const totalWidth = Math.max(xCursor - CLUSTER_GAP_X, leafOrbPx * 4);
    const cx = totalWidth / 2;

    // Central hub stack -- Founder, PA Angella, CEO, Manager, top to
    // bottom, horizontally centered over the whole grid below it.
    const sizePx: Record<"xl" | "lg" | "md", number> = { xl: 150, lg: 118, md: 96 };
    const founderY = 0;
    const paY = founderY + sizePx.xl + leafOrbPx * 0.5;
    const ceoY = paY + sizePx.lg + leafOrbPx * 0.5;
    const managerY = ceoY + sizePx.lg + leafOrbPx * 0.5;
    const labelY = managerY + sizePx.md + leafOrbPx * 1.1;
    const leafY0 = labelY + leafOrbPx * 0.9;
    const leafY1 = leafY0 + GAP_Y;
    const workerY = leafY1 + GAP_Y * 1.3;

    const radarSize = Math.max(totalWidth, workerY - founderY) * 1.4 + 300;
    nodes.push({
      id: "radar-bg", type: "radar",
      position: { x: cx - radarSize / 2, y: (founderY + workerY) / 2 - radarSize / 2 },
      draggable: false, selectable: false, zIndex: -1,
      data: { size: radarSize },
    });

    const stackOrder: { id: string; label: string; sublabel: string; color: string; size: "xl" | "lg" | "md"; active: boolean; y: number }[] = [
      { id: "founder", label: "FOUNDER", sublabel: "", color: "cyan", size: "xl", active: true, y: founderY },
    ];
    // PA Angella -- the founder's own prompt-master PA, always between
    // Founder and CEO. Not part of any squad (she's not a leaf, she's a
    // fixed relay tier), so she's excluded from leafAgents above.
    if (paAgent) stackOrder.push({ id: "pa_angella", label: "PA ANGELLA", sublabel: paAgent.sublabel, color: paAgent.color, size: "lg", active: paAgent.active, y: paY });
    if (ceoAgent) stackOrder.push({ id: "ceo", label: label(ceoAgent), sublabel: ceoAgent.sublabel, color: ceoAgent.color, size: "lg", active: ceoAgent.active, y: ceoY });
    if (managerAgent) stackOrder.push({ id: "manager", label: label(managerAgent), sublabel: managerAgent.sublabel, color: managerAgent.color, size: "md", active: managerAgent.active, y: managerY });

    let hubId = stackOrder[0].id;
    stackOrder.forEach((n, i) => {
      const h = sizePx[n.size];
      nodes.push({
        id: n.id, type: "orb", position: { x: cx - h / 2, y: n.y }, draggable: false,
        data: { label: n.label, sublabel: n.sublabel, color: n.color, size: n.size, active: n.active },
      });
      if (i > 0) {
        edges.push({ id: `e-${stackOrder[i - 1].id}-${n.id}`, source: stackOrder[i - 1].id, target: n.id, type: "flow", data: { color: n.color, active: true } });
      }
      hubId = n.id;
    });

    clusterRanges.forEach((cr) => {
      const midX = (cr.x0 + cr.x1) / 2;
      nodes.push({
        id: `label-${cr.squad}`, type: "label", position: { x: midX - 110 + leafHalf, y: labelY },
        draggable: false, selectable: false, data: { label: cr.squad },
      });
    });

    leafAgents.forEach((a) => {
      const x = xForAgent.get(a.id) ?? 0;
      const y = rowForAgent.get(a.id) === 1 ? leafY1 : leafY0;
      nodes.push({
        id: a.id, type: "orb", position: { x, y }, draggable: false,
        data: { label: label(a), sublabel: a.sublabel, color: a.color, size: leafSize, active: a.active },
      });
      edges.push({ id: `e-${hubId}-${a.id}`, source: hubId, target: a.id, type: "flow", data: { color: a.color, active: a.active } });
    });

    // Worker pools -- one row beneath the whole grid, linked to one real
    // agent per squad that actually feeds that pool (worker_registry.
    // TASK_KINDS' real rapid/engineering/infra split).
    const workerTypes = ["rapid", "engineering", "infra"];
    const servicedBy: Record<string, string[]> = {
      rapid: ["chrome_developer", "finance"], engineering: ["bug_fixer", "website_builder"], infra: ["security", "qa"],
    };
    workerTypes.forEach((wt, i) => {
      const x = cx - leafHalf + (i - 1) * GAP_X * 1.6;
      const busy = status.workers.filter((w) => w.worker_type === wt && w.status === "busy").length;
      const total = status.workers.filter((w) => w.worker_type === wt).length;
      nodes.push({
        id: `worker-${wt}`, type: "orb", position: { x, y: workerY }, draggable: false,
        data: { label: `${wt.toUpperCase()}\nPOOL`, sublabel: `${busy}/${total} busy`, color: "slate", size: leafSize, active: busy > 0 },
      });
      servicedBy[wt].forEach((agentId) => {
        if (leafAgents.some((a) => a.id === agentId)) {
          edges.push({ id: `e-${wt}-${agentId}`, source: agentId, target: `worker-${wt}`, type: "flow", data: { color: "slate", active: busy > 0 } });
        }
      });
    });

    return { nodes, edges };
  }, [status]);

  return (
    <div className="fixed inset-0 overflow-hidden" style={{ background: "radial-gradient(ellipse at 50% 40%, #0d1420 0%, #05070a 70%)" }}>
      <style>{`
        @keyframes radarSpin { to { transform: rotate(360deg); } }
        @keyframes radarRipple {
          0%   { transform: scale(1);   opacity: 0.65; }
          100% { transform: scale(11);  opacity: 0; }
        }
        @keyframes neonOrbit { to { transform: rotate(360deg); } }
      `}</style>

      {mounted && <MatrixRain />}
      {mounted && <FireflySwarm count={160} />}

      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-8 py-5">
        <div>
          <div className="text-[11px] uppercase tracking-[0.25em] text-cyan-400/80 font-mono">{eyebrow}</div>
          <div className="text-xl font-semibold text-slate-100 mt-0.5">{title}</div>
        </div>
        <div className="flex items-center gap-3">
          <AutoRefresh intervalSeconds={1} />
          <a href={backHref} className="text-xs font-mono text-slate-400 hover:text-slate-100 border border-slate-700 rounded-full px-3 py-1.5">
            {backLabel}
          </a>
        </div>
      </div>

      {mounted && (
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={{
            padding: 0.08,
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
