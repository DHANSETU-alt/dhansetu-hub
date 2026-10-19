import Link from "next/link";
import { loadSystemStatus, ACTIVITY_WINDOW_MINUTES } from "@/lib/systemStatus";
import MissionControlFlow from "@/components/MissionControlFlow";
import { ExecutivePanel } from "@/components/ExecutivePanel";
import { getMacRuntime, type MacRuntime } from "@/lib/api";
import { SHAKTHI_OS_VERSION } from "@/lib/version";

export const dynamic = "force-dynamic";

const NAV = [
  ["EXECUTIVE SUITE", [["Living System", "/concept3"], ["Executive Dashboard", "/"], ["Mission Control", "/mission-control"], ["Founder Tasks", "/initiatives"]]],
  ["GOVERNANCE", [["CEO Dashboard", "/ceo"], ["Finance Dashboard", "/finance"], ["Payments", "/payments"], ["Security Dashboard", "/security"], ["Ops Dashboard", "/workers"], ["ERT Command Center", "/ert"]]],
  ["INTELLIGENCE", [["Audit History", "/audits"], ["Correction Bot", "/correction"], ["Failure Analysis Engine", "/failure-analyses"]]],
  ["SYSTEM", [["Settings", "/"], ["Integrations", "/websites"], ["Developer Hub", "/command-center"]]],
] as const;

function ConceptNav({ active }: { active: "living" | "executive" }) {
  return <aside className="concept-nav">
    <div className="concept-brand"><span>⌁</span> SHAKTHI_OS</div>
    <div className="concept-founder"><i>S</i><div><b>HI, FOUNDER</b><small>Executive Core<br/><em /> Online</small></div></div>
    <nav>{NAV.map(([section, links]) => <div key={section}><h3>{section}</h3>{links.map(([label, href]) => {
      const selected = active === "living" ? label === "Living System" : label === "Executive Dashboard";
      return <Link key={label} href={href} className={selected ? "selected" : ""}><span>◈</span>{label}</Link>;
    })}</div>)}</nav>
    <div className="concept-health"><span>System Health</span><b><em /> Mac connected</b></div>
  </aside>;
}

function Metric({ label, value, sub, warn = false }: { label: string; value: string; sub: string; warn?: boolean }) {
  return <div className="hardware-metric"><span>{label}</span><strong className={warn ? "warn" : ""}>{value}</strong><small>{sub}</small></div>;
}

function HardwareBar({ runtime }: { runtime: MacRuntime | null }) {
  const gib = (n: number) => (n / 1073741824).toFixed(1);
  return <footer className="concept-hardware">
    <div className="hardware-title">HARDWARE &amp; SYSTEM HEALTH <i /> <b>{runtime ? "LIVE LOCAL" : "DISCONNECTED"}</b></div>
    <div className="hardware-grid">
      <Metric label="CPU" value={runtime ? `${runtime.cpu_percent}%` : "—"} sub={runtime ? `${runtime.logical_cpus ?? "—"} logical · ${runtime.cpu_name}` : "No Mac sample"}/>
      <Metric label="RAM" value={runtime ? `${runtime.ram_percent}%` : "—"} sub={runtime ? `${gib(runtime.ram_total_bytes)} GiB total` : "No Mac sample"}/>
      <Metric label="STORAGE" value={runtime ? `${runtime.disk_percent}%` : "—"} sub={runtime ? `${gib(runtime.disk_free_bytes)} GiB free` : "No Mac sample"}/>
      <Metric label="GPU" value={runtime?.gpu.state ?? "—"} sub={runtime?.gpu.name ?? runtime?.gpu.reason ?? "No Mac sample"} warn={runtime?.gpu.state !== "CONNECTED"}/>
      <Metric label="BATTERY" value={runtime?.battery_percent == null ? "N/A" : `${runtime.battery_percent}%`} sub={runtime?.battery_plugged == null ? "Not detected" : runtime.battery_plugged ? "AC connected" : "On battery"} warn={runtime?.battery_plugged === false}/>
      <Metric label="HOST" value={runtime?.os ?? "—"} sub={runtime ? `${runtime.kernel} · ${runtime.architecture}` : "No Mac sample"}/>
    </div>
  </footer>;
}

export default async function Concept3Page() {
  const [status, runtime] = await Promise.all([loadSystemStatus(), getMacRuntime().catch(() => null)]);
  return <div className="concept3-shell">
    <header className="concept3-title"><h1>{SHAKTHI_OS_VERSION.osName} CONCEPT 3 — EXECUTIVE NEURAL NETWORK</h1><p>Intelligent. Autonomous. Accountable.</p></header>
    <div className="concept3-workspace">
      <section className="concept3-half"><ConceptNav active="living"/><div className="concept3-stage"><MissionControlFlow status={status} activityWindowMinutes={ACTIVITY_WINDOW_MINUTES} variant="panel" brand={{ eyebrow: "Living System View · LIVE", title: "Real-time neural network activity, flow graph and control plane", backLabel: "", backHref: "#" }}/></div></section>
      <section className="concept3-half"><ConceptNav active="executive"/><div className="concept3-stage"><ExecutivePanel /></div></section>
    </div>
    <HardwareBar runtime={runtime}/>
  </div>;
}
