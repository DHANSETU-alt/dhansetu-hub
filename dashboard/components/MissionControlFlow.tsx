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
  supportServices: { hindsight: string; paperclip: string };
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

function AgentPulseRail({ status }: { status: StatusData }) {
  const latestByAgent = new Map<string, FullTask>();
  for (const task of status.recentActivity) {
    if (!latestByAgent.has(task.agent_id)) latestByAgent.set(task.agent_id, task);
  }

  return (
    <aside
      aria-label="Live agent roster"
      className="absolute right-8 top-40 bottom-24 z-10 hidden w-72 overflow-hidden rounded-xl border border-white/10 bg-[#06090b]/85 shadow-2xl backdrop-blur-md xl:block"
    >
      <div className="flex items-center justify-between border-b border-white/10 px-3 py-2.5">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-[0.16em] text-cyan-300">Live roster</div>
          <div className="mt-0.5 text-[11px] text-slate-500">Real task and heartbeat signals</div>
        </div>
        <span className="rounded-full border border-emerald-400/30 px-2 py-1 text-[9px] font-mono uppercase text-emerald-300">
          {status.kpis.activeAgents} active
        </span>
      </div>
      <div className="h-full overflow-y-auto p-2">
        {status.nodes.map((agent) => {
          const latest = latestByAgent.get(agent.id);
          const tone = agent.active ? "#34d399" : agent.color === "rose" ? "#fb7185" : "#64748b";
          return (
            <div key={agent.id} className="mb-1.5 rounded-lg border border-white/5 bg-white/[0.02] px-2.5 py-2">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: tone, boxShadow: agent.active ? `0 0 9px ${tone}` : "none" }} />
                <span className="min-w-0 flex-1 truncate text-[11px] font-medium text-slate-200">{PERSONA_NAME[agent.id] ?? agent.name}</span>
                <span className="text-[9px] font-mono uppercase" style={{ color: tone }}>{agent.active ? "working" : agent.sublabel}</span>
              </div>
              <div className="mt-1 truncate pl-4 text-[10px] text-slate-500" title={latest?.goal ?? agent.sublabel}>
                {latest ? `${latest.status} · ${latest.goal}` : agent.sublabel}
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}

function AgentMapFallback({ status }: { status: StatusData }) {
  const squads = status.nodes.reduce<Record<string, AgentNode[]>>((groups, agent) => {
    const squad = agent.squad || "Unassigned";
    (groups[squad] ??= []).push(agent);
    return groups;
  }, {});
  return (
    <section
      aria-label="All agents"
      className="absolute left-8 right-[22rem] top-48 bottom-24 z-[1] overflow-y-auto rounded-xl border border-cyan-400/10 bg-black/25 p-3 xl:right-[22rem]"
    >
      <div className="mb-3 flex items-center justify-between px-1">
        <span className="text-[10px] font-mono uppercase tracking-[0.16em] text-slate-500">Agent execution map</span>
        <span className="text-[10px] font-mono text-slate-600">live roster · {status.nodes.length} registered</span>
      </div>
      <div className="mb-4 flex items-center justify-center gap-3 text-[10px] font-mono uppercase tracking-[0.14em]">
        <div className="rounded-lg border border-cyan-400/50 bg-cyan-400/10 px-4 py-2 text-cyan-300 shadow-[0_0_18px_rgba(34,211,238,0.14)]">Founder</div>
        <motion.div animate={{ opacity: [0.25, 1, 0.25] }} transition={{ duration: 1.2, repeat: Infinity }} className="h-px w-10 bg-cyan-300 shadow-[0_0_9px_#22d3ee]" />
        <div className="rounded-lg border border-violet-400/50 bg-violet-400/10 px-4 py-2 text-violet-300 shadow-[0_0_18px_rgba(167,139,250,0.14)]">Orchestrator</div>
        <motion.div animate={{ opacity: [0.25, 1, 0.25] }} transition={{ duration: 1.2, repeat: Infinity, delay: 0.3 }} className="h-px w-10 bg-violet-300 shadow-[0_0_9px_#a78bfa]" />
        <div className="rounded-lg border border-emerald-400/50 bg-emerald-400/10 px-4 py-2 text-emerald-300 shadow-[0_0_18px_rgba(52,211,153,0.14)]">Agent pool</div>
      </div>
      <div className="space-y-3 border-t border-violet-400/20 pt-3">
        {Object.entries(squads).map(([squad, agents]) => (
          <div key={squad} className="relative rounded-lg border border-white/5 bg-white/[0.015] p-2 pl-4">
            <div className="absolute bottom-3 left-1.5 top-8 w-px bg-gradient-to-b from-violet-400/70 via-cyan-400/40 to-transparent" />
            <div className="mb-2 flex items-center gap-2 text-[9px] font-mono uppercase tracking-[0.14em] text-violet-300">
              <span className="h-1.5 w-1.5 rounded-full bg-violet-300 shadow-[0_0_8px_#a78bfa]" /> {squad} lane · {agents.length} agents
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5">
              {agents.map((agent) => {
                const color = GLOW[agent.color] || GLOW.slate;
                return (
                  <motion.div key={agent.id} initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} className="relative rounded-lg border px-2.5 py-2" style={{ borderColor: `${color}55`, background: `${color}0b`, boxShadow: agent.active ? `0 0 16px ${color}44` : "none" }}>
                    <motion.span animate={{ opacity: agent.active ? [0.35, 1, 0.35] : 0.45 }} transition={{ duration: 1.1, repeat: Infinity }} className="absolute -left-2 top-1/2 h-px w-2 bg-cyan-300 shadow-[0_0_8px_#22d3ee]" />
                    <div className="flex items-center gap-2"><span className="h-2 w-2 shrink-0 rounded-full" style={{ background: color, boxShadow: agent.active ? `0 0 8px ${color}` : "none" }} /><span className="truncate text-[11px] font-medium text-slate-200">{PERSONA_NAME[agent.id] ?? agent.name}</span></div>
                    <div className="mt-1 truncate pl-4 text-[9px] font-mono uppercase" style={{ color }}>{agent.active ? "working now" : agent.sublabel}</div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
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

// Real spinning-strand motion for DNA-helix members: a full circular orbit
// path sampled into keyframes (framer-motion animates a straight tween
// between each pair, so enough steps are needed for it to read as a smooth
// circle, not a polygon). `phase0` staggers strand A vs strand B 180 deg
// apart so a rung's two nodes visibly orbit as a rotating pair.
const ORBIT_STEPS = 13;
function orbitKeyframes(radius: number, phase0: number) {
  const xs: number[] = [];
  const ys: number[] = [];
  for (let i = 0; i < ORBIT_STEPS; i++) {
    const a = phase0 + (i / (ORBIT_STEPS - 1)) * Math.PI * 2;
    xs.push(radius * Math.cos(a));
    ys.push(radius * Math.sin(a));
  }
  return { xs, ys };
}

// --- Custom node: a glowing glass orb, pulses when recently active ---
function OrbNode({ data }: NodeProps) {
  const d = data as unknown as {
    label: string; sublabel: string; color: string; size: "xl" | "lg" | "md" | "sm" | "xs"; active: boolean; face?: string;
    orbitRadius?: number; orbitPhase0?: number;
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

  // DNA-helix members carry real orbit data instead -- a continuous
  // circular path around their own fixed anchor point, replacing the
  // float/sway wobble with a real visible spin.
  const hasOrbit = typeof d.orbitRadius === "number";
  const orbit = hasOrbit ? orbitKeyframes(d.orbitRadius as number, d.orbitPhase0 ?? 0) : null;

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
        animate={hasOrbit ? { x: orbit!.xs, y: orbit!.ys } : { y: [0, -floatAmp, 0, floatAmp * 0.5, 0], x: [0, swayAmp, 0, -swayAmp * 0.6, 0] }}
        transition={hasOrbit ? { duration: 7, repeat: Infinity, ease: "linear" } : { duration: floatDuration, delay: floatDelay, repeat: Infinity, ease: "easeInOut" }}
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
  const d = data as unknown as { color: string; active: boolean; chaseOffset?: number } | undefined;
  const glow = GLOW[d?.color || "slate"] || GLOW.slate;
  const [path] = getStraightPath({ sourceX, sourceY, targetX, targetY });
  const motionPath = `M${sourceX},${sourceY} L${targetX},${targetY}`;
  // Ferris-wheel rim edges pass a chaseOffset (0-1, this edge's position
  // around the ring) so each segment's traveling dot starts later than the
  // last -- the same two dots-per-edge timing, just phase-shifted per rim
  // segment, so light visibly chases all the way around the wheel instead
  // of every spoke pulsing in lockstep.
  const chase = d?.chaseOffset ?? 0;

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
                begin={`${((offset + chase) % 1) * 1.6}s`}
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

// --- Living-system core: a pulsing energy center with a real 3D pyramid
// slowly rotating on its own vertical axis, centered on the founder node.
// An original visual design for this project -- not a reproduction of any
// existing character or franchise's reactor/HUD art. Lives INSIDE React
// Flow's own node space (not a plain absolutely-positioned div over the
// container) so it pans/zooms/fits in lockstep with the rest of the graph
// instead of drifting independently of it. Keeps the radar sweep, breathing
// glow and sonar ripples from the earlier ring-based core -- only the
// concentric rings themselves were swapped for the pyramid (founder ask,
// 2026-09-12: "3D Pyramid look ... in slow motion rotating"). ---
function CoreNode({ data }: NodeProps) {
  const d = data as unknown as { size: number; width?: number; height?: number };
  const w = d.width ?? d.size;
  const h = d.height ?? d.size;
  // Four faces built with the classic CSS border-triangle trick (a
  // zero-size box whose left/right borders are transparent and bottom
  // border is solid, rendering a triangle). All four start stacked at the
  // exact same point -- bottom-center of the wrapper -- so `transform-origin:
  // bottom` gives every face the SAME pivot point; that shared pivot is what
  // lets rotateY turn them around one common central axis instead of each
  // spinning around its own base. `translateZ` then pushes each face
  // outward along its (already Y-rotated) local axis before `rotateX` tilts
  // it back to form the slope -- translateZ = halfBase * tan(tilt) is the
  // exact distance that makes the four tilted faces meet edge-to-edge into
  // a real square footprint at that tilt angle, not an approximation.
  const halfBase = 70;
  const tiltDeg = 30;
  const faceHeight = Math.round(halfBase * 2 * 0.866); // equilateral-ish face
  const translateZ = Math.round(halfBase * Math.tan((tiltDeg * Math.PI) / 180));
  return (
    <div style={{ width: w, height: h, pointerEvents: "none", position: "relative" }}>
      {/* Faint background sweep, same technique as before -- one slow wedge
          of light circling the whole core, underneath the rings. */}
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: "conic-gradient(from 0deg, transparent 0deg, rgba(34,211,238,0.22) 14deg, transparent 70deg)",
          animation: "radarSpin 7s linear infinite",
          mixBlendMode: "screen",
        }}
      />
      {/* Breathing core glow -- dead center, scales/fades in a slow cycle so
          the whole view reads as "alive" even with no recent task activity.
          Fixed size (not size-relative) for the same reason as the rings. */}
      <div
        className="absolute rounded-full"
        style={{
          left: "50%", top: "50%", width: 130, height: 130,
          marginLeft: -65, marginTop: -65,
          background: "radial-gradient(circle, rgba(34,211,238,0.85) 0%, rgba(34,211,238,0.25) 55%, transparent 75%)",
          filter: "blur(1px)",
          animation: "coreBreathe 3.6s ease-in-out infinite",
        }}
      />
      {/* 3D rotating pyramid -- the living system's core structure. Wrapper
          carries `perspective` (required on the parent of a preserve-3d
          element for the depth to actually render) and sits centered on the
          founder orb, same anchor point the old rings used. */}
      <div
        className="absolute"
        style={{
          left: "50%", top: "50%",
          marginLeft: -halfBase, marginTop: -faceHeight / 2,
          width: halfBase * 2, height: faceHeight,
          perspective: 900,
        }}
      >
        <div
          className="absolute inset-0"
          style={{ transformStyle: "preserve-3d", animation: "pyramidSpin 26s linear infinite" }}
        >
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              style={{
                position: "absolute", bottom: 0, left: "50%", marginLeft: -halfBase,
                width: 0, height: 0,
                borderLeft: `${halfBase}px solid transparent`,
                borderRight: `${halfBase}px solid transparent`,
                borderBottom: `${faceHeight}px solid rgba(34,211,238,0.32)`,
                transformOrigin: "bottom",
                transform: `rotateY(${i * 90}deg) translateZ(${-translateZ}px) rotateX(${tiltDeg}deg)`,
                filter: "drop-shadow(0 0 14px rgba(34,211,238,0.8))",
              }}
            />
          ))}
        </div>
      </div>
      {/* Sonar-ping ripples, same as before -- discrete pulses expanding
          outward from center, a different rhythm than the continuous ring
          spin so the core reads as both "running" and "actively pinging." */}
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="absolute rounded-full"
          style={{
            left: "50%", top: "50%", width: 24, height: 24, marginLeft: -12, marginTop: -12,
            border: "2px solid rgba(103,232,249,0.75)",
            animation: `radarRipple 3.2s ease-out ${i * 1.05}s infinite`,
          }}
        />
      ))}
    </div>
  );
}

const nodeTypes = { orb: OrbNode, radar: CoreNode, label: SquadLabelNode };
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

    // Radial hub-and-spoke layout, restored to the original design
    // (founder correction, 2026-09-03: "Mission Control's only and only
    // agents [should be in the] animated rotating DNA type... remaining
    // don't change single thing"). Hub stack, worker-pool ring, squad
    // label positions and radar backdrop are all back to exactly how the
    // pre-helix version computed them -- ONLY the individual squad-member
    // agents get the DNA treatment, as a small rotating double helix
    // radiating outward along each squad's own spoke.
    const N = Math.max(leafAgents.length, 1);
    const leafSize: "sm" | "xs" = N > 24 ? "xs" : "sm";
    const leafOrbPx = leafSize === "xs" ? 66 : 78;
    const numSquads = Math.max(squadKeys.length, 1);

    const nodes: Node[] = [];
    const edges: Edge[] = [];

    // Explicit left-to-right flow: Founder relay on the left, squad lanes on
    // the right. Keeping these anchors in columns makes every connection
    // readable as a directed workflow instead of a floating orbit.
    const cx = -560, cy = 0;
    const sizePx: Record<"xl" | "lg" | "md", number> = { xl: 150, lg: 118, md: 96 };
    // Cluster ring: how far each squad's center sits from the hub. Scales
    // with squad count so more squads don't overlap each other.
    const CLUSTER_RADIUS = 360;
    // Member ring: how far a squad's own agents sit from THEIR squad's
    // angular position (also anchors the helix's outward extent below).
    const MEMBER_RADIUS = leafOrbPx * 1.9;

    const angleStep = 0;
    const startAngle = 0;

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

    // Per-squad Ferris wheel: a small always-lit axle node at the squad's
    // cluster center, members evenly spaced around a rim circle -- spoke
    // edges (axle -> member) plus rim edges (member -> next member,
    // closing the loop) so it reads as an actual wheel, not just agents in
    // a circle. Real motion comes from two safe, proven techniques: each
    // gondola gets a small continuous spin-in-place via the same
    // orbitKeyframes/OrbNode mechanism the DNA helix used (node.position
    // stays fully static -- recomputing position via a timer was tried
    // earlier and broke ReactFlow's internal visibility tracking), and the
    // neon flow's traveling dot chases all the way around the rim loop
    // (each rim edge's dot phase-shifted by its position around the ring
    // via `chaseOffset`, consumed in FlowEdge) so light visibly flows
    // around the wheel continuously -- the real "merry-go-round" read.
    const WHEEL_RADIUS_LOCAL = MEMBER_RADIUS;
    const GONDOLA_SPIN_RADIUS = leafOrbPx * 0.28;

    squadKeys.forEach((squad, si) => {
      const members = bySquad.get(squad)!;
      const clusterX = 280 + si * 290;
      const clusterY = 0;

      nodes.push({
        id: `label-${squad}`, type: "label", position: { x: clusterX - 110, y: clusterY - leafOrbPx * 1.5 },
        draggable: false, selectable: false, data: { label: squad },
      });

      // Axle: the wheel's true center. Unlabeled, small, always lit -- the
      // hub chain connects here, and every spoke/rim edge anchors off it.
      const axleId = `axle-${squad}`;
      const squadActive = members.some((m) => m.active);
      const squadColor = members[0]?.color ?? "slate";
      nodes.push({
        id: axleId, type: "orb", position: { x: clusterX, y: clusterY }, draggable: false,
        data: { label: "", sublabel: "", color: squadColor, size: "xs", active: squadActive },
      });
      edges.push({ id: `e-${hubId}-axle-${squad}`, source: hubId, target: axleId, type: "flow", data: { color: squadColor, active: squadActive } });

      members.forEach((m, mi) => {
        const memberAngle = 0;
        const mx = clusterX;
        const my = clusterY + (mi - (members.length - 1) / 2) * 112;
        nodes.push({
          id: m.id, type: "orb", position: { x: mx, y: my }, draggable: false,
          data: { label: label(m), face: face(m), sublabel: m.sublabel, color: m.color, size: leafSize, active: m.active, orbitRadius: GONDOLA_SPIN_RADIUS, orbitPhase0: memberAngle },
        });
        // Spoke: axle -> this gondola. Real active-state signal lives here.
        edges.push({ id: `spoke-${squad}-${m.id}`, source: axleId, target: m.id, type: "flow", data: { color: m.color, active: m.active } });
        // Rim: this gondola -> the next one around the wheel, wrapping to
        // the first -- always "active" (it's the wheel's own structure
        // lighting up, not an individual agent's task state), phase-offset
        // by position around the ring so the chase reads as one continuous
        // loop of light.
        if (members.length > 1) {
          const next = members[(mi + 1) % members.length];
          edges.push({
            id: `rim-${squad}-${m.id}-${next.id}`, source: m.id, target: next.id,
            type: "flow", data: { color: m.color, active: true, chaseOffset: mi / members.length },
          });
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
      className={`${variant === "fullscreen" ? "fixed inset-x-0 bottom-0 top-9" : "relative w-full h-full"} overflow-hidden`}
      style={{ background: variant === "fullscreen" ? "#020303" : "transparent" }}
    >
      <style>{`
        @keyframes radarSpin { to { transform: rotate(360deg); } }
        @keyframes radarRipple {
          0%   { transform: scale(1);   opacity: 0.65; }
          100% { transform: scale(11);  opacity: 0; }
        }
        @keyframes neonOrbit { to { transform: rotate(360deg); } }
        @keyframes coreBreathe {
          0%, 100% { transform: scale(0.85); opacity: 0.55; }
          50%      { transform: scale(1.15); opacity: 1; }
        }
        @keyframes pyramidSpin { to { transform: rotateY(360deg); } }
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
          <AutoRefresh intervalSeconds={3} />
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

      <div className="absolute top-32 left-8 z-10 flex gap-2 text-[10px] font-mono uppercase tracking-[0.12em]">
        {(["paperclip", "hindsight"] as const).map((service) => {
          const state = status.supportServices[service];
          const reachable = state === "reachable";
          return (
            <span key={service} className="rounded-full border px-2 py-1" style={{ borderColor: reachable ? "rgba(52,211,153,0.45)" : "rgba(148,163,184,0.25)", color: reachable ? "#6ee7b7" : "#94a3b8" }}>
              {service} · {state}
            </span>
          );
        })}
      </div>

      <AgentPulseRail status={status} />
      <AgentMapFallback status={status} />

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
