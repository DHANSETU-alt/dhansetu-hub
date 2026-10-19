"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  type FullTask, type TaskLogEvent, type CommandCenterResult, type AgentHealth,
} from "@/lib/api";

// Real "needs founder attention" row from the backend's own decisions table
// (orchestrator/db.py recent_decisions) -- status is one of
// approved | rejected | revise, decided by the real CEO agent per
// agents/ceo.yaml ("revise means the goal is worth pursuing but is
// underspecified or risky as written"). Not a fabricated approvals queue.
type Decision = {
  id: number;
  task_id: number;
  goal: string;
  status: "approved" | "rejected" | "revise" | string;
  priority_score: number | null;
  risk_score: number | null;
  business_impact_score: number | null;
  reason: string | null;
  created_at: string;
};

const NEON_VIOLET = "#b985ff";
const NEON_CYAN = "#5ef1ff";
const NEON_PINK = "#ff5ec4";
const POLL_MS = 6000;
const TOKEN_KEY = "shakthi_cc_token";

// Real DB status is only ever pending/done/failed (see orchestrator/db.py
// tasks table) -- extending it to a persisted 6-state lifecycle would mean
// writing an intermediate status mid-dispatch from inside
// routing.run_task(), the single most heavily-used function in this
// 25-agent system, and auditing every existing consumer of task status
// (at least one real COUNT(*) WHERE status='pending' query exists). That's
// real, broad blast radius for a UI feature -- not worth it tonight, and
// the founder's own brief says "prefer simple, reliable... do not rewrite
// working code." So this lifecycle is honestly DERIVED from two real
// signals (status, created_at) instead of persisted. "Assigned" isn't
// shown as its own lane: this system's dispatch is synchronous and always
// assigns an agent at task creation (insert_task always takes agent_id),
// so there is no real gap between "created" and "assigned" to observe --
// showing one would be fabricating a state, not deriving it.
const NEW_WINDOW_SECONDS = 3;
const RUNNING_WINDOW_SECONDS = 25;

type Lane = "NEW" | "RUNNING" | "WAITING" | "COMPLETED" | "FAILED";
const LANES: Lane[] = ["NEW", "RUNNING", "WAITING", "COMPLETED", "FAILED"];
const LANE_COLOR: Record<Lane, string> = {
  NEW: "#8a8fa3",
  RUNNING: NEON_CYAN,
  WAITING: "#ffcf4f",
  COMPLETED: "#4fffa0",
  FAILED: NEON_PINK,
};

function ageSeconds(iso: string): number {
  const t = Date.parse(iso.endsWith("Z") ? iso : iso + "Z");
  if (Number.isNaN(t)) return 0;
  return Math.max(0, (Date.now() - t) / 1000);
}

function deriveLane(t: FullTask): Lane {
  if (t.status === "done") return "COMPLETED";
  if (t.status === "failed") return "FAILED";
  const age = ageSeconds(t.created_at);
  if (age < NEW_WINDOW_SECONDS) return "NEW";
  if (age < RUNNING_WINDOW_SECONDS) return "RUNNING";
  return "WAITING"; // still pending well past the normal dispatch window -- real signal something is stuck
}

// Priority is REAL and stored -- orchestrator/routing.py's classify_risk()
// now returns one of 4 real values (low/normal/high/critical), written to
// tasks.risk_level on every dispatch. The critical-keyword list and the
// cloud-escalation gate (`risk == "critical"`) are byte-for-byte
// unchanged, so this extension cannot change which tasks escalate to
// cloud -- only "high"/"low" are new classification bands for goals that
// don't hit a critical keyword.
const PRIORITY_ORDER = ["critical", "high", "normal", "low"];
const PRIORITY_COLOR: Record<string, string> = {
  critical: NEON_PINK,
  high: "#ff9f4f",
  normal: "#8a8fa3",
  low: "#5a6078",
};

// Founder-facing roster labels mapped onto the REAL 25-agent roster --
// nothing here is a fabricated placeholder agent. Mapping choices
// explained in the build report: Master Coordinator is the real
// Shakthi_Agent -> CEO dispatch chain (pa_angella internally); Code/Design map to the closest real
// engineering-layer agents; Security/Finance/Marketing are exact 1:1
// matches; System Watchdog is a real deterministic subsystem
// (orchestrator/watchdog.py) rather than an LLM agent, so it has no
// `agents` table row and no live task-based health signal -- shown as a
// static subsystem entry, not faked as an active agent.
const ROSTER: { label: string; agentIds: string[]; subsystem?: boolean }[] = [
  { label: "Master Coordinator", agentIds: ["ceo", "pa_angella"] },
  { label: "Code Agent", agentIds: ["engineer", "bug_fixer"] },
  { label: "Design Agent", agentIds: ["website_builder", "chrome_developer"] },
  { label: "Security Agent", agentIds: ["security"] },
  { label: "Finance Agent", agentIds: ["finance"] },
  { label: "Marketing Agent", agentIds: ["marketing"] },
  { label: "System Watchdog", agentIds: [], subsystem: true },
];

// Real, file-backed v5.1 status -- see app/api/shakthi-v5/status/route.ts.
// Every field is read from a real file (TASK_1_WATCHDOG_STATUS.md,
// data/failure-memory.json) at request time, not hardcoded here.
type ShakthiV5Status = {
  mode: string;
  activeTask: string;
  topBlocker: string;
  buildTestStatus: string;
  failureMemoryCount: number | null;
  failureMemoryError: string | null;
  readiness: { done: number; total: number; percent: number; criteria: { item: string; done: boolean; evidence: string }[] };
};

export default function CommandCenterPage() {
  const [tasks, setTasks] = useState<FullTask[]>([]);
  const [logs, setLogs] = useState<TaskLogEvent[]>([]);
  const [agentHealth, setAgentHealth] = useState<AgentHealth[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [apiDown, setApiDown] = useState(false);
  const [v5Status, setV5Status] = useState<ShakthiV5Status | null>(null);
  const [v5Error, setV5Error] = useState("");
  const [showCriteria, setShowCriteria] = useState(false);

  const [command, setCommand] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CommandCenterResult | null>(null);
  const [submitError, setSubmitError] = useState("");

  const [token, setToken] = useState("");
  const [tokenDraft, setTokenDraft] = useState("");
  const [showTokenBox, setShowTokenBox] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const saved = typeof window !== "undefined" ? window.localStorage.getItem(TOKEN_KEY) : null;
    if (saved) setToken(saved);
  }, []);

  const load = useCallback(async (tok: string) => {
    // Routed through /api/command-center/state (a same-origin Next.js
    // route), not the direct-to-8787 lib/api.ts helpers -- a real browser
    // fetch from this client component to 127.0.0.1:8787 is killed by
    // Chrome's Private Network Access preflight (confirmed live: zero
    // network entries, a bare "TypeError: Failed to fetch"), the same
    // issue website-health/refresh/route.ts already works around. The
    // proxy route does the actual 8787 calls server-side, where Node has
    // no such restriction.
    const qs = tok ? `?token=${encodeURIComponent(tok)}` : "";
    try {
      const res = await fetch(`/api/command-center/state${qs}`, { cache: "no-store" });
      if (!res.ok) { setApiDown(true); return; }
      const data = await res.json();
      if (data.error || !data.tasks) { setApiDown(true); return; }
      setApiDown(false);
      setTasks(data.tasks);
      setLogs(data.events || []);
      setAgentHealth(data.agents || []);
      setDecisions(data.decisions || []);
    } catch {
      setApiDown(true);
    }
  }, []);

  useEffect(() => {
    load(token);
    const id = setInterval(() => load(token), POLL_MS);
    return () => clearInterval(id);
  }, [load, token]);

  // Same-origin route reading real local files server-side -- no
  // private-network-access issue like the :8787 calls above, so a plain
  // client fetch is fine here.
  useEffect(() => {
    let cancelled = false;
    fetch("/api/shakthi-v5/status", { cache: "no-store" })
      .then((r) => r.json())
      .then((d) => { if (!cancelled) setV5Status(d); })
      .catch((e) => { if (!cancelled) setV5Error(e instanceof Error ? e.message : "v5 status fetch failed"); });
    return () => { cancelled = true; };
  }, []);

  function saveToken() {
    window.localStorage.setItem(TOKEN_KEY, tokenDraft);
    setToken(tokenDraft);
    setShowTokenBox(false);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = command.trim();
    if (!text || submitting) return;
    setSubmitting(true);
    setSubmitError("");
    setResult(null);
    try {
      const qs = new URLSearchParams({ text, ...(token ? { token } : {}) });
      const res = await fetch(`/api/command-center/submit?${qs.toString()}`, { cache: "no-store" });
      const r = await res.json();
      if (r.error) setSubmitError(r.error);
      else {
        setResult(r);
        setCommand("");
        load(token);
      }
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "submit failed");
    } finally {
      setSubmitting(false);
      inputRef.current?.focus();
    }
  }

  const byLane: Record<Lane, FullTask[]> = { NEW: [], RUNNING: [], WAITING: [], COMPLETED: [], FAILED: [] };
  for (const t of tasks) byLane[deriveLane(t)].push(t);
  for (const lane of LANES) {
    byLane[lane].sort((a, b) => PRIORITY_ORDER.indexOf(a.risk_level) - PRIORITY_ORDER.indexOf(b.risk_level));
  }

  const healthByAgent = Object.fromEntries(agentHealth.map((a) => [a.id, a]));
  const pendingApprovals = decisions.filter((d) => d.status === "revise");

  return (
    <div
      className="min-h-screen -m-8 p-4 sm:p-8 font-mono"
      style={{
        background: "radial-gradient(ellipse 120% 80% at 50% -10%, #140a29 0%, #04010a 55%, #000000 100%)",
        color: "#dfe6ff",
      }}
    >
      <div className="mb-4 flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1
            className="text-xl sm:text-2xl font-bold tracking-widest uppercase"
            style={{ color: NEON_VIOLET, textShadow: `0 0 14px ${NEON_VIOLET}88, 0 0 2px ${NEON_VIOLET}` }}
          >
            Founder Command Center
          </h1>
          <p className="text-xs mt-1 tracking-wide" style={{ color: "#7a80a0" }}>
            One agent. One command center. Complete business execution. Real dispatch -&gt; Shakthi_Agent -&gt; local model -&gt; task board. no marketing copy, this is the cockpit.
          </p>
        </div>
        <button
          onClick={() => { setTokenDraft(token); setShowTokenBox((s) => !s); }}
          className="text-[10px] px-2 py-1 rounded border shrink-0"
          style={{ borderColor: "#ffffff22", color: token ? "#4fffa0" : "#7a80a0" }}
        >
          {token ? "LAN TOKEN SET" : "SET LAN TOKEN"}
        </button>
      </div>

      {/* Current task / system status / pending approvals -- real signals,
          not decorative. System status mirrors the same apiDown check the
          rest of this page already relies on; Pending Approvals is the real
          "revise" decision queue (see Decision type above). */}
      <div className="mb-6 grid grid-cols-2 sm:grid-cols-3 gap-2">
        <div className="rounded border p-2" style={{ borderColor: "#ffffff16", background: "#05030c" }}>
          <div className="text-[10px] uppercase tracking-wide" style={{ color: "#7a80a0" }}>System status</div>
          <div className="mt-1 flex items-center gap-1.5 text-sm font-bold" style={{ color: apiDown ? NEON_PINK : "#4fffa0" }}>
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: apiDown ? NEON_PINK : "#4fffa0", boxShadow: apiDown ? "none" : "0 0 6px #4fffa0" }} />
            {apiDown ? "OFFLINE" : "ONLINE"}
          </div>
        </div>
        <div className="rounded border p-2" style={{ borderColor: "#ffffff16", background: "#05030c" }}>
          <div className="text-[10px] uppercase tracking-wide" style={{ color: "#7a80a0" }}>Current task load</div>
          <div className="mt-1 text-sm font-bold" style={{ color: NEON_CYAN }}>{byLane.NEW.length + byLane.RUNNING.length} in flight</div>
        </div>
        <div className="rounded border p-2" style={{ borderColor: pendingApprovals.length ? "#ffcf4f55" : "#ffffff16", background: "#05030c" }}>
          <div className="text-[10px] uppercase tracking-wide" style={{ color: "#7a80a0" }}>Pending approvals</div>
          <div className="mt-1 text-sm font-bold" style={{ color: pendingApprovals.length ? "#ffcf4f" : "#4fffa0" }}>{pendingApprovals.length} need review</div>
        </div>
      </div>

      {/* SHAKTHI_OS v5.1 Agent Control -- every value below is read from a
          real file (docs/v3.4/TASK_1_WATCHDOG_STATUS.md, data/failure-memory.json)
          by app/api/shakthi-v5/status/route.ts at request time. Approval
          queue is NOT duplicated here -- it links to the real Pending
          Approvals panel already on this page (see pendingApprovals below). */}
      <div className="mb-6 rounded-md border" style={{ borderColor: `${NEON_VIOLET}33`, background: "#03020a" }}>
        <div className="px-3 py-2 text-xs font-bold tracking-widest uppercase" style={{ color: NEON_VIOLET, borderBottom: `1px solid ${NEON_VIOLET}22` }}>
          SHAKTHI_OS v5.1 Agent Control
        </div>
        {v5Error && !v5Status && <div className="p-3 text-xs" style={{ color: NEON_PINK }}>v5 status unavailable: {v5Error}</div>}
        {v5Status && (
          <div className="p-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div className="rounded border p-2" style={{ borderColor: "#ffffff16", background: "#05030c" }}>
                <div className="text-[10px] uppercase tracking-wide" style={{ color: "#7a80a0" }}>Mode</div>
                <div className="mt-1" style={{ color: "#c7cbe6" }}>{v5Status.mode}</div>
              </div>
              <div className="rounded border p-2" style={{ borderColor: "#ffffff16", background: "#05030c" }}>
                <div className="text-[10px] uppercase tracking-wide" style={{ color: "#7a80a0" }}>Build/test</div>
                <div className="mt-1 font-bold" style={{ color: v5Status.buildTestStatus === "pass" ? "#4fffa0" : v5Status.buildTestStatus === "fail" ? NEON_PINK : "#7a80a0" }}>
                  {v5Status.buildTestStatus.toUpperCase()}
                </div>
              </div>
              <div className="rounded border p-2" style={{ borderColor: "#ffffff16", background: "#05030c" }}>
                <div className="text-[10px] uppercase tracking-wide" style={{ color: "#7a80a0" }}>Failure memory</div>
                <div className="mt-1" style={{ color: "#c7cbe6" }}>
                  {v5Status.failureMemoryCount === null ? "not yet tracked" : `${v5Status.failureMemoryCount} entries`}
                </div>
              </div>
              <button
                onClick={() => setShowCriteria((s) => !s)}
                className="rounded border p-2 text-left"
                style={{ borderColor: "#ffffff16", background: "#05030c" }}
              >
                <div className="text-[10px] uppercase tracking-wide" style={{ color: "#7a80a0" }}>Task 1 readiness</div>
                <div className="mt-1 font-bold" style={{ color: NEON_CYAN }}>
                  {v5Status.readiness.done}/{v5Status.readiness.total} &middot; {v5Status.readiness.percent}%
                </div>
              </button>
            </div>
            <div className="mt-2 rounded border p-2 text-xs" style={{ borderColor: "#ffcf4f33", background: "#120e02" }}>
              <span className="uppercase tracking-wide text-[10px]" style={{ color: "#ffcf4f" }}>Active task &middot; top blocker</span>
              <div className="mt-1" style={{ color: "#c7cbe6" }}>{v5Status.activeTask}</div>
              <div className="mt-1" style={{ color: "#ffcf4f" }}>{v5Status.topBlocker}</div>
              <div className="mt-1 opacity-60">
                Approval queue: see &quot;Pending approvals&quot; below ({pendingApprovals.length} awaiting review) &mdash; not duplicated here.
              </div>
            </div>
            {showCriteria && (
              <div className="mt-2 rounded border p-2 text-[11px] space-y-1" style={{ borderColor: "#ffffff16", background: "#05030c" }}>
                {v5Status.readiness.criteria.map((c) => (
                  <div key={c.item} className="flex gap-2">
                    <span style={{ color: c.done ? "#4fffa0" : NEON_PINK }}>{c.done ? "✓" : "✗"}</span>
                    <span style={{ color: "#c7cbe6" }}>{c.item}</span>
                    <span className="opacity-40 truncate">— {c.evidence}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {showTokenBox && (
        <div className="mb-4 flex flex-wrap items-center gap-2 rounded border p-3 text-xs" style={{ borderColor: "#ffffff22", background: "#070212" }}>
          <span style={{ color: "#7a80a0" }}>
            Only needed when opening this page over LAN/mobile (non-loopback). Matches SHAKTHI_API_TOKEN on the server. Stored only in this browser's localStorage.
          </span>
          <input
            type="password"
            value={tokenDraft}
            onChange={(e) => setTokenDraft(e.target.value)}
            placeholder="paste SHAKTHI_API_TOKEN"
            className="flex-1 min-w-[160px] bg-transparent border rounded px-2 py-1 outline-none"
            style={{ borderColor: `${NEON_CYAN}44`, color: "#eaf6ff" }}
          />
          <button onClick={saveToken} className="px-2 py-1 rounded border" style={{ borderColor: NEON_CYAN, color: NEON_CYAN }}>SAVE</button>
        </div>
      )}

      {apiDown && (
        <div className="mb-6 px-4 py-3 rounded border text-sm" style={{ borderColor: NEON_PINK, color: NEON_PINK, background: "#1a0510" }}>
          API unreachable{token ? " (or LAN token is wrong/missing)" : ""}. Start it with <code>python3 -m orchestrator.api</code>.
        </div>
      )}

      {/* Agent roster strip */}
      <div className="mb-6 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
        {ROSTER.map((r) => {
          const live = r.agentIds.map((id) => healthByAgent[id]).filter(Boolean) as AgentHealth[];
          const active = live.some((a) => a.last_activity && ageSeconds(a.last_activity) < 300);
          return (
            <div key={r.label} className="rounded border p-2 text-[10px]" style={{ borderColor: "#ffffff16", background: "#05030c" }}>
              <div className="flex items-center gap-1.5">
                <span
                  className="w-1.5 h-1.5 rounded-full shrink-0"
                  style={{ background: r.subsystem ? "#5a6078" : active ? "#4fffa0" : "#5a6078", boxShadow: active ? "0 0 6px #4fffa0" : "none" }}
                />
                <span className="uppercase tracking-wide truncate" style={{ color: "#c7cbe6" }}>{r.label}</span>
              </div>
              <div className="mt-1 opacity-50 truncate">
                {r.subsystem ? "deterministic subsystem" : r.agentIds.join(" + ")}
              </div>
            </div>
          );
        })}
      </div>

      {/* Command input */}
      <form
        onSubmit={handleSubmit}
        className="mb-6 flex items-center gap-3 rounded-md border p-3"
        style={{ borderColor: `${NEON_CYAN}33`, background: "#070212", boxShadow: `0 0 24px ${NEON_VIOLET}22 inset` }}
      >
        <span style={{ color: NEON_CYAN }}>&gt;</span>
        <input
          ref={inputRef}
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          placeholder="Ask Shakthi_Agent anything..."
          disabled={submitting}
          className="flex-1 min-w-0 bg-transparent outline-none text-sm placeholder:opacity-40"
          style={{ color: "#eaf6ff" }}
        />
        <button
          type="submit"
          disabled={submitting || !command.trim()}
          className="px-4 py-1.5 text-xs font-bold uppercase tracking-widest rounded border disabled:opacity-40 shrink-0"
          style={{ borderColor: NEON_VIOLET, color: submitting ? "#8a8fa3" : NEON_VIOLET }}
        >
          {submitting ? "..." : "Ask Shakthi_Agent"}
        </button>
      </form>

      {submitError && <div className="mb-6 text-sm" style={{ color: NEON_PINK }}>ERROR: {submitError}</div>}

      {result && (
        <div className="mb-6 rounded-md border p-4 text-sm space-y-2" style={{ borderColor: `${NEON_CYAN}33`, background: "#050a12" }}>
          <div><span style={{ color: NEON_CYAN }}>SHAKTHI_AGENT REFINED &rarr;</span> {result.refined_prompt}</div>
          <div className="flex flex-wrap gap-3 text-xs pt-1" style={{ color: "#9aa0c0" }}>
            <span>ceo status: <b style={{ color: result.ceo_decision.status === "approve" ? "#4fffa0" : "#ffcf4f" }}>{result.ceo_decision.status}</b></span>
            <span>priority: {result.ceo_decision.priority_score ?? "—"}</span>
            <span>risk: {result.ceo_decision.risk_score ?? "—"}</span>
            <span>impact: {result.ceo_decision.business_impact_score ?? "—"}</span>
            <span>pa #{result.pa_task_id}</span>
            <span>ceo #{result.ceo_decision.task_id}</span>
          </div>
          {result.ceo_decision.reason && <div style={{ color: "#c7cbe6" }}>{result.ceo_decision.reason}</div>}
        </div>
      )}

      {/* Pending approvals -- real "revise" decisions from the CEO agent,
          not a fabricated approvals queue. Empty when nothing needs review. */}
      {pendingApprovals.length > 0 && (
        <div className="mb-6 rounded-md border" style={{ borderColor: "#ffcf4f33", background: "#120e02" }}>
          <div className="px-3 py-2 text-xs font-bold tracking-widest uppercase" style={{ color: "#ffcf4f", borderBottom: "1px solid #ffcf4f22" }}>
            Pending approvals // {pendingApprovals.length} awaiting founder review
          </div>
          <div className="p-2 space-y-2 max-h-[260px] overflow-y-auto">
            {pendingApprovals.map((d) => (
              <div key={d.id} className="rounded p-2 text-xs border" style={{ borderColor: "#ffcf4f33", background: "#0a0a14" }}>
                <div className="flex items-center justify-between gap-2">
                  <span style={{ color: "#ffcf4f" }}>decision #{d.id} &middot; task #{d.task_id}</span>
                  <span className="opacity-40">{d.created_at}</span>
                </div>
                <div className="mt-1" style={{ color: "#c7cbe6" }}>{d.goal}</div>
                {d.reason && <div className="mt-1 opacity-70">{d.reason}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Task board */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
        {LANES.map((lane) => (
          <div key={lane} className="rounded-md border" style={{ borderColor: `${LANE_COLOR[lane]}33`, background: "#05030c" }}>
            <div
              className="px-3 py-2 text-xs font-bold tracking-widest uppercase flex items-center justify-between"
              style={{ color: LANE_COLOR[lane], borderBottom: `1px solid ${LANE_COLOR[lane]}22` }}
            >
              <span>{lane}</span>
              <span>{byLane[lane].length}</span>
            </div>
            <div className="p-2 space-y-2 max-h-[420px] overflow-y-auto">
              {byLane[lane].length === 0 && <div className="text-xs px-2 py-3 opacity-30">empty</div>}
              {byLane[lane].map((t) => (
                <div
                  key={t.id}
                  className="rounded p-2 text-xs border"
                  style={{
                    borderColor: t.risk_level === "critical" ? `${NEON_PINK}55` : "#ffffff11",
                    background: t.risk_level === "critical" ? "#1a0510" : "#0a0a14",
                  }}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span style={{ color: NEON_CYAN }}>{t.agent_id}</span>
                    <span
                      className="px-1.5 py-0.5 rounded text-[10px] uppercase font-bold"
                      style={{ color: PRIORITY_COLOR[t.risk_level] ?? "#8a8fa3", border: `1px solid ${(PRIORITY_COLOR[t.risk_level] ?? "#8a8fa3")}55` }}
                    >
                      {t.risk_level}
                    </span>
                  </div>
                  <div className="mt-1 truncate" style={{ color: "#c7cbe6" }} title={t.goal}>{t.goal}</div>
                  <div className="mt-1 opacity-40">#{t.id} &middot; {t.created_at}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Activity timeline -- real task_events, newest activity from Shakthi_Agent's dispatch chain */}
      <div className="rounded-md border" style={{ borderColor: `${NEON_VIOLET}33`, background: "#03020a" }}>
        <div className="px-3 py-2 text-xs font-bold tracking-widest uppercase" style={{ color: NEON_VIOLET, borderBottom: `1px solid ${NEON_VIOLET}22` }}>
          SHAKTHI_AGENT ACTIVITY TIMELINE // real task_events, polling every {POLL_MS / 1000}s
        </div>
        <div className="p-3 space-y-1 max-h-[320px] overflow-y-auto text-[11px] sm:text-xs">
          {logs.length === 0 && <div className="opacity-30">no events yet</div>}
          {logs.map((e) => (
            <div key={e.id} className="flex gap-2 sm:gap-3 flex-wrap">
              <span className="opacity-40 shrink-0">{e.created_at}</span>
              <span className="shrink-0 font-bold" style={{ color: { dispatch: NEON_CYAN, result: "#4fffa0", validate_fail: "#ffcf4f", escalate: NEON_PINK }[e.event_type] ?? "#8a8fa3" }}>
                [{e.event_type}]
              </span>
              <span className="opacity-70 shrink-0">{e.agent_id}</span>
              <span className="truncate" style={{ color: "#c7cbe6" }}>{e.goal}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
