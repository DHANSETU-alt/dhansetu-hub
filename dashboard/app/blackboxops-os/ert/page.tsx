import Link from "next/link";
import { getIncidents } from "@/lib/api";

export const dynamic = "force-dynamic";

const SEVERITY_COLOR: Record<string, string> = { P0: "#f87171", P1: "#f87171", P2: "#dba956", P3: "#8b95a6", P4: "#8b95a6" };

export default async function BlackboxErtPage() {
  const { incidents, open_count, critical_count, mttr_seconds } = await getIncidents(undefined, undefined, 30).catch(
    () => ({ incidents: [], open_count: 0, critical_count: 0, mttr_seconds: null })
  );

  return (
    <div className="fixed inset-0 overflow-y-auto" style={{ background: "#0a0c10", color: "#e8ecf1" }}>
      <div className="max-w-4xl mx-auto px-8 py-10">
        <Link href="/blackboxops-os" className="text-xs font-mono text-[#8b95a6] hover:text-white">← blackboxOps_OS</Link>
        <h1 className="text-3xl font-semibold mt-4 mb-2">ERT Center</h1>
        <p className="text-sm text-[#a8b1c2] mb-8">Every incident gets an owner, a backup, an escalation path, and — once resolved — a postmortem. Automatically.</p>

        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="rounded-xl border border-[#1e232e] p-5" style={{ background: "#0f131a" }}>
            <div className="text-[11px] uppercase tracking-wide text-[#8b95a6]">Open</div>
            <div className="text-2xl font-semibold font-mono mt-1">{open_count}</div>
          </div>
          <div className="rounded-xl border border-[#1e232e] p-5" style={{ background: "#0f131a" }}>
            <div className="text-[11px] uppercase tracking-wide text-[#8b95a6]">Critical</div>
            <div className="text-2xl font-semibold font-mono mt-1" style={{ color: critical_count ? "#f87171" : "#4ade80" }}>{critical_count}</div>
          </div>
          <div className="rounded-xl border border-[#1e232e] p-5" style={{ background: "#0f131a" }}>
            <div className="text-[11px] uppercase tracking-wide text-[#8b95a6]">MTTR</div>
            <div className="text-2xl font-semibold font-mono mt-1">{mttr_seconds ? `${Math.round(mttr_seconds / 60)}m` : "—"}</div>
          </div>
        </div>

        {incidents.length === 0 ? (
          <p className="text-sm text-[#8b95a6]">No incidents on record.</p>
        ) : (
          <div className="space-y-2">
            {incidents.map((inc) => (
              <div key={inc.id} className="rounded-lg border border-[#1e232e] px-4 py-3 flex items-center justify-between" style={{ background: "#0f131a" }}>
                <span className="text-sm">{inc.incident_number} · {inc.incident_type.replace(/_/g, " ")}</span>
                <div className="flex items-center gap-3 text-xs font-mono">
                  <span style={{ color: SEVERITY_COLOR[inc.severity] }}>{inc.severity}</span>
                  <span className="text-[#8b95a6]">{inc.status}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
