"use client";

import { use, useEffect, useMemo, useState } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { motion } from "framer-motion";
import { BrainCircuit, CheckCircle2, CircleAlert, RotateCcw, ShieldCheck, Sparkles } from "lucide-react";
import "@xyflow/react/dist/style.css";

type Phase = "plan" | "do" | "check" | "why" | "react";

type LiveStatus = {
  nodes: Array<{ id: string; active: boolean; sublabel: string }>;
  kpis: { totalAgents: number; activeAgents: number; successRatePercent: number | null; bottleneckCount: number };
  sentinelOk: boolean;
};

type LoopEvent = { id: number; event_type: string; payload: string; created_at: string; agent_id: string };
type RoutePreview = { risk: string; agent: { id: string; name: string; layer: string; allowed_tools: string[] } };

const PHASES: Array<{ id: Phase; label: string; color: string; description: string }> = [
  { id: "plan", label: "PLAN", color: "#7dd3fc", description: "Break the mission into bounded, reversible steps." },
  { id: "do", label: "DO", color: "#a78bfa", description: "Route each step to the best specialist and tool." },
  { id: "check", label: "CHECK", color: "#34d399", description: "Verify outputs, health signals, cost, and policy." },
  { id: "why", label: "WHY ×3", color: "#fbbf24", description: "Trace the root cause before applying a patch." },
  { id: "react", label: "REACT", color: "#fb7185", description: "Heal, rollback, escalate, and learn from the result." },
];

function phaseColor(id: Phase) { return PHASES.find((phase) => phase.id === id)?.color ?? "#94a3b8"; }

function AgentNode({ data }: NodeProps) {
  const item = data as unknown as { phase: Phase; label: string; detail: string; active: boolean; icon: string };
  const color = phaseColor(item.phase);
  return (
    <motion.div
      animate={item.active ? { y: [0, -5, 0], boxShadow: [`0 0 0 ${color}22`, `0 0 32px ${color}66`, `0 0 0 ${color}22`] } : { y: 0 }}
      transition={{ duration: 2.4, repeat: item.active ? Infinity : 0, ease: "easeInOut" }}
      className="relative w-[190px] rounded-2xl border bg-[#071016]/95 px-4 py-3 backdrop-blur-xl"
      style={{ borderColor: `${color}88` }}
    >
      <Handle type="target" position={Position.Left} style={{ background: color, border: 0 }} />
      <Handle type="source" position={Position.Right} style={{ background: color, border: 0 }} />
      <div className="flex items-center gap-2 text-xs font-semibold" style={{ color }}><span>{item.icon}</span>{item.label}</div>
      <div className="mt-2 text-[11px] leading-4 text-slate-300">{item.detail}</div>
      <div className="mt-3 flex items-center gap-1.5 text-[10px] uppercase tracking-[.14em] text-slate-500">
        <span className={`h-1.5 w-1.5 rounded-full ${item.active ? "animate-pulse" : ""}`} style={{ background: color }} />
        {item.active ? "working" : "standby"}
      </div>
    </motion.div>
  );
}

const nodeTypes = { agent: AgentNode };

export default function JarvisMissionGraph({ status }: { status: Promise<LiveStatus> }) {
  const [activePhase, setActivePhase] = useState<Phase>("plan");
  const [whyIteration, setWhyIteration] = useState(0);
  const [mission, setMission] = useState("Audit every Dhansetu launch path and repair the highest-risk failure.");
  const [running, setRunning] = useState(false);
  const [dispatchState, setDispatchState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [dispatchMessage, setDispatchMessage] = useState("");
  const [events, setEvents] = useState<LoopEvent[]>([]);
  const [routePreview, setRoutePreview] = useState<RoutePreview | null>(null);
  // The page supplies the same live status snapshot used by Mission Control.
  // The graph keeps its control-loop state local while its safety indicators
  // and KPI strip come from the real orchestrator response.
  const liveStatus = use(status);

  async function refreshEvents() {
    const response = await fetch("/api/command-center/logs?limit=8", { cache: "no-store" });
    if (!response.ok) return;
    const data = await response.json() as { events?: LoopEvent[] };
    setEvents(data.events ?? []);
  }

  useEffect(() => {
    const timer = window.setTimeout(() => { void refreshEvents(); }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      const response = await fetch(`/api/jarvis/route?text=${encodeURIComponent(mission)}`, { cache: "no-store" });
      if (response.ok) setRoutePreview(await response.json() as RoutePreview);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [mission]);

  const nodes = useMemo<Node[]>(() => PHASES.map((phase, index) => ({
    id: phase.id,
    type: "agent",
    position: { x: index * 240, y: 150 + (index % 2) * 30 },
    data: { phase: phase.id, label: phase.label, detail: phase.description, active: running && activePhase === phase.id, icon: ["◈", "✦", "✓", "⌁", "↻"][index] },
  })), [activePhase, running]);

  const edges = useMemo<Edge[]>(() => PHASES.slice(0, -1).map((phase, index) => ({
    id: `${phase.id}-${PHASES[index + 1].id}`,
    source: phase.id,
    target: PHASES[index + 1].id,
    animated: running && index < PHASES.findIndex((item) => item.id === activePhase),
    style: { stroke: phaseColor(PHASES[index + 1].id), strokeWidth: 2 },
  })), [activePhase, running]);

  async function runNext() {
    setRunning(true);
    setDispatchState("sending");
    setDispatchMessage("");
    const index = PHASES.findIndex((phase) => phase.id === activePhase);
    const phase = PHASES[index];
    try {
      const response = await fetch(`/api/command-center/submit?text=${encodeURIComponent(`Shakthi_Agent ${phase.label}: ${mission}`)}`);
      const data = await response.json() as { ceo_decision?: { status?: string; reason?: string }; error?: string };
      if (!response.ok || data.error) throw new Error(data.error || `Dispatch returned ${response.status}`);
      if (phase.id === "check") {
        const health = await fetch("/api/sentinel/collect", { cache: "no-store" });
        if (!health.ok) throw new Error(`Sentinel verification returned ${health.status}`);
        const healthData = await health.json() as { snapshot?: { health_score?: number } };
        const score = healthData.snapshot?.health_score;
        setDispatchMessage(`CHECK verified${typeof score === "number" ? ` · Sentinel ${score}/100` : ""}.`);
      }
      setDispatchState("sent");
      if (phase.id !== "check") setDispatchMessage(`${phase.label} recorded${data.ceo_decision?.status ? ` · CEO ${data.ceo_decision.status}` : ""}.`);
      if (phase.id === "why" && whyIteration < 2) {
        setWhyIteration((value) => value + 1);
      } else {
        setWhyIteration(0);
        setActivePhase(PHASES[(index + 1) % PHASES.length].id);
      }
      void refreshEvents();
    } catch (error) {
      setDispatchState("error");
      setDispatchMessage(error instanceof Error ? error.message : "Dispatch failed");
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-2 flex flex-wrap gap-2"><span className="rounded-full border border-cyan-300/30 bg-cyan-300/10 px-2 py-1 text-[10px] uppercase tracking-[.16em] text-cyan-200">Shakthi_Agent / OpenClaw Core</span><span className="rounded-full border border-emerald-300/30 bg-emerald-300/10 px-2 py-1 text-[10px] uppercase tracking-[.16em] text-emerald-200">Self-healing loop</span></div>
          <h1 className="text-3xl font-semibold tracking-tight">Mission Graph</h1>
          <p className="mt-1 max-w-2xl text-sm text-[var(--muted-foreground)]">One control loop for planning, execution, verification, root-cause analysis, and recovery across every Shakthi agent.</p>
        </div>
        <button onClick={runNext} disabled={dispatchState === "sending"} className="inline-flex items-center justify-center gap-2 rounded-xl border border-cyan-300/40 bg-cyan-300/10 px-4 py-2 text-sm text-cyan-100 hover:bg-cyan-300/20 disabled:cursor-wait disabled:opacity-60"><Sparkles size={16} />{dispatchState === "sending" ? "Dispatching…" : running ? "Advance loop" : "Run Shakthi_Agent loop"}</button>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_300px]">
        <section className="overflow-hidden rounded-2xl border border-white/10 bg-[#05090d]">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3"><div className="flex items-center gap-2 text-sm text-slate-200"><BrainCircuit size={17} className="text-cyan-300" /> Langflow view · live control plane</div><span className="font-mono text-[10px] text-slate-500">MISSION-LOOP-001</span></div>
          <div className="h-[420px]">
            <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.25 }} nodesDraggable={false} nodesConnectable={false} zoomOnDoubleClick={false}>
              <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#1e3440" />
              <Controls showInteractive={false} />
            </ReactFlow>
          </div>
        </section>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-white/10 bg-[var(--surface)] p-4"><div className="mb-3 flex items-center gap-2 text-sm font-semibold"><ShieldCheck size={17} className="text-emerald-300" /> Safety envelope</div><div className="space-y-2 text-xs text-[var(--muted-foreground)]"><div className="flex justify-between"><span>Tool policy</span><b className="text-emerald-300">enforced</b></div><div className="flex justify-between"><span>Rollback point</span><b className="text-emerald-300">ready</b></div><div className="flex justify-between"><span>Human escalation</span><b className="text-cyan-300">armed</b></div></div></div>
          <div className="rounded-2xl border border-white/10 bg-[var(--surface)] p-4"><div className="mb-3 text-sm font-semibold">Mission input</div><textarea value={mission} onChange={(event) => setMission(event.target.value)} className="min-h-28 w-full resize-none rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-[var(--ink)] outline-none focus:border-cyan-300/50" /><div className="mt-3 flex items-center gap-2 text-xs text-[var(--muted-foreground)]"><CircleAlert size={14} className="text-amber-300" />Every step is logged before it runs.</div>{routePreview && <div className="mt-3 rounded-xl border border-cyan-300/15 bg-cyan-300/5 p-3 text-xs"><div className="flex items-center justify-between"><span className="text-slate-400">Routing preview</span><b className={routePreview.risk === "critical" ? "text-rose-300" : "text-amber-300"}>{routePreview.risk}</b></div><div className="mt-2 text-cyan-100">{routePreview.agent.name}</div><div className="mt-1 text-slate-500">{routePreview.agent.layer} · {routePreview.agent.allowed_tools.length} tools</div></div>}</div>
        </aside>
      </div>

      <div className="grid gap-3 md:grid-cols-5">{PHASES.map((phase) => <button key={phase.id} onClick={() => { setActivePhase(phase.id); if (phase.id !== "why") setWhyIteration(0); }} className={`rounded-xl border p-3 text-left transition ${activePhase === phase.id ? "bg-white/10" : "bg-[var(--surface)] hover:bg-white/5"}`} style={{ borderColor: activePhase === phase.id ? `${phase.color}99` : "rgba(255,255,255,.1)" }}><div className="text-[10px] font-mono tracking-[.15em]" style={{ color: phase.color }}>{phase.label}{phase.id === "why" && activePhase === "why" ? ` · ${whyIteration + 1}/3` : ""}</div><div className="mt-2 text-xs text-[var(--muted-foreground)]">{phase.description}</div></button>)}</div>
      <div className="grid gap-3 sm:grid-cols-4">
        <div className="rounded-xl border border-white/10 bg-[var(--surface)] p-3"><div className="text-[10px] uppercase tracking-[.14em] text-slate-500">Agent roster</div><div className="mt-1 text-xl font-semibold">{liveStatus.kpis.totalAgents}</div><div className="text-xs text-slate-500">{liveStatus.kpis.activeAgents} active now</div></div>
        <div className="rounded-xl border border-white/10 bg-[var(--surface)] p-3"><div className="text-[10px] uppercase tracking-[.14em] text-slate-500">Recovery mode</div><div className="mt-1 text-xl font-semibold text-emerald-300">Armed</div><div className="text-xs text-slate-500">Rollback before retry</div></div>
        <div className="rounded-xl border border-white/10 bg-[var(--surface)] p-3"><div className="text-[10px] uppercase tracking-[.14em] text-slate-500">Success rate</div><div className="mt-1 text-xl font-semibold text-amber-300">{liveStatus.kpis.successRatePercent === null ? "—" : `${liveStatus.kpis.successRatePercent}%`}</div><div className="text-xs text-slate-500">From real task ledger</div></div>
        <div className="rounded-xl border border-white/10 bg-[var(--surface)] p-3"><div className="text-[10px] uppercase tracking-[.14em] text-slate-500">Sentinel</div><div className="mt-1 text-xl font-semibold text-cyan-300">{liveStatus.sentinelOk ? "Connected" : "Unknown"}</div><div className="text-xs text-slate-500">Runtime health feed</div></div>
      </div>
      <section className="rounded-2xl border border-white/10 bg-[var(--surface)] p-4"><div className="mb-3 flex items-center justify-between"><div className="text-sm font-semibold">Recent loop evidence</div><span className="text-[10px] uppercase tracking-[.14em] text-slate-500">task event ledger</span></div>{events.length ? <div className="space-y-2">{events.map((event) => <div key={event.id} className="flex items-center gap-3 rounded-lg border border-white/5 bg-black/10 px-3 py-2 text-xs"><span className="h-1.5 w-1.5 rounded-full bg-cyan-300" /><b className="text-cyan-200">{event.event_type}</b><span className="truncate text-slate-400">{event.payload}</span><span className="ml-auto shrink-0 font-mono text-[10px] text-slate-600">{event.agent_id}</span></div>)}</div> : <div className="text-xs text-slate-500">No loop events yet. Run a mission phase to create the first evidence record.</div>}</section>
      <div className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-sm ${dispatchState === "error" ? "border-rose-300/20 bg-rose-300/5 text-rose-100" : "border-emerald-300/20 bg-emerald-300/5 text-emerald-100"}`}><CheckCircle2 size={17} />Current gate: <b>{PHASES.find((phase) => phase.id === activePhase)?.label}</b><span className="text-emerald-200/60">· root cause evidence is required before recovery.</span>{dispatchMessage && <span className="ml-auto text-xs opacity-80">{dispatchMessage}</span>}<RotateCcw size={15} className="ml-auto text-emerald-300" /></div>
    </div>
  );
}
