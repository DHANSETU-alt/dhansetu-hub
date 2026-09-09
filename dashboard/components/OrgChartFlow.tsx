"use client";

import { useMemo } from "react";
import {
  ReactFlow, Background, BackgroundVariant, Handle, Position,
  type Node, type Edge, type NodeProps, BaseEdge, getSmoothStepPath,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { Agent } from "@/lib/api";

// Real top-down org flow chart, per founder instruction 2026-09-09:
// "make dashboard like flow chart format, 1 Angella flow 2 CEO's than
// flow 2 teams both CEO's." Deliberately simple/hierarchical -- distinct
// from MissionControlFlow.tsx's radial "living system" wheel, which stays
// as-is (not touched, not replaced) since it's tuned, working, and
// answers a different question ("who's active right now") than this page
// answers ("how does the org actually report up").
//
// pa_angella_2 exists as a real registered agent (Team 2's mirror, same
// as every other Team-2 agent) but is deliberately NOT rendered as a
// second top node here -- the real chain of command is one Angella
// overseeing both CEOs, not two Angellas. That's a visualization choice
// about what this chart is showing, not a claim pa_angella_2 doesn't
// exist in the registry (it does, same as any other Team 2 agent).

const GLOW: Record<string, string> = { cyan: "#22d3ee", violet: "#a78bfa", amber: "#fbbf24" };

function OrgNode({ data }: NodeProps) {
  const d = data as unknown as { label: string; sublabel: string; color: string; size: "xl" | "lg" | "sm" };
  const glow = GLOW[d.color] || "#94a3b8";
  const dims = { xl: 140, lg: 100, sm: 64 }[d.size];
  const fontSize = { xl: 15, lg: 12, sm: 9 }[d.size];
  return (
    <div style={{ width: dims, height: dims, position: "relative" }} className="flex items-center justify-center">
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
      <div
        className="absolute inset-0 rounded-full backdrop-blur-md flex flex-col items-center justify-center text-center px-1.5"
        style={{
          background: `radial-gradient(circle at 35% 30%, ${glow}44, rgba(8,10,16,0.9) 70%)`,
          border: `2px solid ${glow}aa`,
          boxShadow: `0 0 24px ${glow}55, inset 0 0 18px ${glow}30`,
        }}
      >
        <span className="font-semibold leading-tight" style={{ fontSize, color: "#f8fafc" }}>{d.label}</span>
        {d.sublabel && <span className="mt-0.5 leading-tight font-mono" style={{ fontSize: fontSize - 3, color: glow }}>{d.sublabel}</span>}
      </div>
    </div>
  );
}

function TreeEdge({ sourceX, sourceY, targetX, targetY, data }: { sourceX: number; sourceY: number; targetX: number; targetY: number; data?: { color?: string } }) {
  const glow = GLOW[data?.color || ""] || "#3b4454";
  const [path] = getSmoothStepPath({ sourceX, sourceY, targetX, targetY, borderRadius: 12 });
  return <BaseEdge path={path} style={{ stroke: `${glow}88`, strokeWidth: 2 }} />;
}

const nodeTypes = { org: OrgNode };
const edgeTypes = { tree: TreeEdge };

export function OrgChartFlow({ agents }: { agents: Agent[] }) {
  const { nodes, edges } = useMemo(() => {
    const isTeam2 = (a: Agent) => a.id.endsWith("_2");
    const ceo1 = agents.find((a) => a.id === "ceo");
    const ceo2 = agents.find((a) => a.id === "ceo_2");
    const angella = agents.find((a) => a.id === "pa_angella");
    const team1 = agents.filter((a) => !isTeam2(a) && a.id !== "ceo" && a.id !== "pa_angella");
    const team2 = agents.filter((a) => isTeam2(a) && a.id !== "ceo_2" && a.id !== "pa_angella_2");

    const nodes: Node[] = [];
    const edges: Edge[] = [];
    const COLS = 6;
    const COL_GAP = 150;
    const ROW_GAP = 130;

    if (angella) {
      nodes.push({ id: "angella", type: "org", position: { x: 0, y: 0 }, draggable: false,
        data: { label: "ANGELLA", sublabel: "Orchestrator", color: "violet", size: "xl" } });
    }

    const teamOffsetX = COLS * COL_GAP * 0.7;
    [{ ceo: ceo1, team: team1, side: -1, tag: "Team 1" }, { ceo: ceo2, team: team2, side: 1, tag: "Team 2" }].forEach(({ ceo, team, side, tag }) => {
      if (!ceo) return;
      const ceoX = side * teamOffsetX;
      const ceoY = 220;
      nodes.push({ id: ceo.id, type: "org", position: { x: ceoX, y: ceoY }, draggable: false,
        data: { label: "CEO", sublabel: tag, color: "cyan", size: "lg" } });
      edges.push({ id: `angella-${ceo.id}`, source: "angella", target: ceo.id, type: "tree", data: { color: "violet" } });

      const teamTop = ceoY + 200;
      const gridWidth = (COLS - 1) * COL_GAP;
      team.forEach((agent, i) => {
        const col = i % COLS;
        const row = Math.floor(i / COLS);
        const x = ceoX - gridWidth / 2 + col * COL_GAP;
        const y = teamTop + row * ROW_GAP;
        nodes.push({ id: agent.id, type: "org", position: { x, y }, draggable: false,
          data: { label: agent.name.replace(" (Team 2)", "").replace("Shakthi ", "").replace("Dhansetu ", ""), sublabel: agent.squad?.split("—")[0].trim() ?? "", color: "amber", size: "sm" } });
        edges.push({ id: `${ceo.id}-${agent.id}`, source: ceo.id, target: agent.id, type: "tree", data: { color: "amber" } });
      });
    });

    return { nodes, edges };
  }, [agents]);

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.15}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
        nodesConnectable={false}
        elementsSelectable={false}
      >
        <Background variant={BackgroundVariant.Dots} gap={28} size={1} color="#1e293b" />
      </ReactFlow>
    </div>
  );
}
