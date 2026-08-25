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

// --- Custom node: a glowing glass orb, pulses when recently active ---
function OrbNode({ data }: NodeProps) {
  const d = data as unknown as {
    label: string; sublabel: string; color: string; size: "xl" | "lg" | "md" | "sm"; active: boolean;
  };
  const glow = GLOW[d.color] || GLOW.slate;
  // Bumped up across the board -- 17 nodes on screen at once means "small"
  // was the real complaint, not just a preference.
  const dims = { xl: 150, lg: 118, md: 96, sm: 78 }[d.size];
  const fontSize = { xl: 18, lg: 15, md: 12.5, sm: 11 }[d.size];

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
          style={{ boxShadow: `0 0 0 1px ${glow}66` }}
          animate={{ scale: [1, 1.4, 1], opacity: [0.7, 0, 0.7] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        />
      )}
      <div
        className="absolute inset-0 rounded-full backdrop-blur-md"
        style={{
          background: `radial-gradient(circle at 35% 30%, ${glow}44, rgba(8,10,16,0.85) 70%)`,
          border: `1.5px solid ${glow}88`,
          boxShadow: `0 0 30px ${glow}66, 0 0 60px ${glow}22, inset 0 0 26px ${glow}30`,
        }}
      />
      <div className="relative z-10 flex flex-col items-center text-center px-1.5 select-none">
        <span className="font-semibold leading-tight" style={{ fontSize, color: "#f8fafc" }}>{d.label}</span>
        {d.sublabel && (
          <span className="mt-1 leading-tight font-mono" style={{ fontSize: fontSize - 3.5, color: glow }}>{d.sublabel}</span>
        )}
      </div>
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
      <BaseEdge path={path} style={{ stroke: `${glow}55`, strokeWidth: 3.5 }} />
      {d?.active && (
        <>
          <path
            d={path}
            fill="none"
            stroke={glow}
            strokeWidth={4.5}
            strokeDasharray="10 12"
            strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 8px ${glow})` }}
          >
            <animate attributeName="stroke-dashoffset" from="44" to="0" dur="1.1s" repeatCount="indefinite" />
          </path>
          {[0, 0.5].map((offset) => (
            <circle key={offset} r="5.5" fill={glow} style={{ filter: `drop-shadow(0 0 9px ${glow})` }}>
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
const NODE_GAP_X = 138;
const CLUSTER_GAP_X = 120;

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

    // Pyramid shape: every squad's members wrap into 2 rows instead of one
    // flat wide row. Roughly halves the widest row's width (and so the
    // whole diagram's total width), which is what actually lets fitView
    // show every corner without zooming out past readable -- a single
    // abrupt jump from Manager (1 node) straight to one very wide leaf row
    // read as a lollipop, not a taper. Two graduated leaf rows underneath
    // Founder -> PA -> CEO -> Manager -> squad labels reads as an actual
    // pyramid. Orb styling, glow, and neon edge flow are untouched --
    // this only changes node x/y placement.
    const ROWS_PER_CLUSTER = 2;
    const ROW_GAP_Y = 120;

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
          xForAgent.set(m.id, xCursor + colIdx * NODE_GAP_X);
          rowForAgent.set(m.id, rowIdx);
        });
      });
      xCursor += maxRowLen * NODE_GAP_X;
      clusterRanges.push({ squad, x0: start, x1: xCursor - NODE_GAP_X });
      xCursor += CLUSTER_GAP_X;
    });
    const totalWidth = Math.max(xCursor - CLUSTER_GAP_X, 300);
    const cx = totalWidth / 2;
    const xOffset = 0;

    const founderY = 10, paY = 195, ceoY = 385, managerY = 565, labelY = 720;
    const leafY0 = 795, leafY1 = leafY0 + ROW_GAP_Y, workerY = leafY1 + 230;

    const nodes: Node[] = [];
    const edges: Edge[] = [];

    const radarSize = Math.max(totalWidth, 700) + 400;
    nodes.push({
      id: "radar-bg", type: "radar",
      position: { x: cx - radarSize / 2, y: (leafY1 + founderY) / 2 - radarSize / 2 },
      draggable: false, selectable: false, zIndex: -1,
      data: { size: radarSize },
    });

    nodes.push({
      id: "founder", type: "orb", position: { x: cx - 75, y: founderY }, draggable: false,
      data: { label: "FOUNDER", sublabel: "", color: "cyan", size: "xl", active: true },
    });

    let hubId = "founder";
    let hubColor = "cyan";

    // PA Angella -- the founder's own prompt-master PA, always between
    // Founder and CEO. Not part of any squad (she's not a leaf, she's a
    // fixed relay tier), so she's excluded from leafAgents above and gets
    // her own position here instead.
    if (paAgent) {
      nodes.push({
        id: "pa_angella", type: "orb", position: { x: cx - 59, y: paY }, draggable: false,
        data: { label: "PA ANGELLA", sublabel: paAgent.sublabel, color: paAgent.color, size: "lg", active: paAgent.active },
      });
      edges.push({ id: "e-founder-pa", source: "founder", target: "pa_angella", type: "flow", data: { color: "cyan", active: true } });
      hubId = "pa_angella";
      hubColor = paAgent.color;
    }

    if (ceoAgent) {
      nodes.push({
        id: "ceo", type: "orb", position: { x: cx - 59, y: ceoY }, draggable: false,
        data: { label: label(ceoAgent), sublabel: ceoAgent.sublabel, color: ceoAgent.color, size: "lg", active: ceoAgent.active },
      });
      edges.push({ id: "e-pa-ceo", source: hubId, target: "ceo", type: "flow", data: { color: hubColor, active: true } });
      hubId = "ceo";
      hubColor = ceoAgent.color;
    }

    if (managerAgent) {
      nodes.push({
        id: "manager", type: "orb", position: { x: cx - 48, y: managerY }, draggable: false,
        data: { label: label(managerAgent), sublabel: managerAgent.sublabel, color: managerAgent.color, size: "md", active: managerAgent.active },
      });
      edges.push({ id: "e-ceo-manager", source: hubId, target: "manager", type: "flow", data: { color: hubColor, active: managerAgent.active } });
      hubId = "manager";
      hubColor = managerAgent.color;
    }

    clusterRanges.forEach((cr) => {
      const midX = xOffset + (cr.x0 + cr.x1) / 2;
      nodes.push({
        id: `label-${cr.squad}`, type: "label", position: { x: midX - 110 + 39, y: labelY },
        draggable: false, selectable: false, data: { label: cr.squad },
      });
    });

    leafAgents.forEach((a) => {
      const x = xOffset + (xForAgent.get(a.id) ?? 0);
      const y = rowForAgent.get(a.id) === 1 ? leafY1 : leafY0;
      nodes.push({
        id: a.id, type: "orb", position: { x, y }, draggable: false,
        data: { label: label(a), sublabel: a.sublabel, color: a.color, size: "sm", active: a.active },
      });
      edges.push({ id: `e-${hubId}-${a.id}`, source: hubId, target: a.id, type: "flow", data: { color: a.color, active: a.active } });
    });

    // Worker pools -- unchanged concept from before, now anchored under the
    // whole tree rather than a separate outer ring, linked to one real
    // agent per squad that actually feeds that pool (worker_registry.
    // TASK_KINDS' real rapid/engineering/infra split).
    const workerTypes = ["rapid", "engineering", "infra"];
    const servicedBy: Record<string, string[]> = {
      rapid: ["chrome_developer", "finance"], engineering: ["bug_fixer", "website_builder"], infra: ["security", "qa"],
    };
    workerTypes.forEach((wt, i) => {
      const x = cx - 39 + (i - 1) * 230;
      const busy = status.workers.filter((w) => w.worker_type === wt && w.status === "busy").length;
      const total = status.workers.filter((w) => w.worker_type === wt).length;
      nodes.push({
        id: `worker-${wt}`, type: "orb", position: { x, y: workerY }, draggable: false,
        data: { label: `${wt.toUpperCase()}\nPOOL`, sublabel: `${busy}/${total} busy`, color: "slate", size: "sm", active: busy > 0 },
      });
      servicedBy[wt].forEach((agentId) => {
        if (xForAgent.has(agentId)) {
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
      `}</style>

      {mounted && <MatrixRain />}
      {mounted && <FireflySwarm count={160} />}

      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-8 py-5">
        <div>
          <div className="text-[11px] uppercase tracking-[0.25em] text-cyan-400/80 font-mono">{eyebrow}</div>
          <div className="text-xl font-semibold text-slate-100 mt-0.5">{title}</div>
        </div>
        <div className="flex items-center gap-3">
          <AutoRefresh intervalSeconds={3} />
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
