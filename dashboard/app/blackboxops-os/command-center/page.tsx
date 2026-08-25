import Link from "next/link";
import { getGovernorStatus, getCeoHealth, getIncidents, getWorkers } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function BlackboxCommandCenterPage() {
  const [governor, ceoHealth, incidentsResult, workersResult] = await Promise.all([
    getGovernorStatus().catch(() => null),
    getCeoHealth().catch(() => null),
    getIncidents().catch(() => null),
    getWorkers(20).catch(() => null),
  ]);

  const tiles = [
    { label: "Governor", value: governor?.status ?? "—", good: governor?.status === "operational" },
    { label: "CEO Health", value: ceoHealth?.status ?? "—", good: ceoHealth?.status === "healthy" },
    { label: "Open Incidents", value: incidentsResult ? String(incidentsResult.open_count) : "—", good: (incidentsResult?.open_count ?? 0) === 0 },
    { label: "Worker Queue", value: workersResult ? String(workersResult.load_balancer.queue_depth) : "—", good: !workersResult?.load_balancer.overflowing },
  ];

  return (
    <div className="fixed inset-0 overflow-y-auto" style={{ background: "#0a0c10", color: "#e8ecf1" }}>
      <div className="max-w-5xl mx-auto px-8 py-10">
        <Link href="/blackboxops-os" className="text-xs font-mono text-[#8b95a6] hover:text-white">← blackboxOps_OS</Link>
        <h1 className="text-3xl font-semibold mt-4 mb-2">Command Center</h1>
        <p className="text-sm text-[#a8b1c2] mb-8">Real, live status from the same orchestrator this whole product runs on — not a mockup.</p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {tiles.map((t) => (
            <div key={t.label} className="rounded-xl border border-[#1e232e] p-5" style={{ background: "#0f131a" }}>
              <div className="text-[11px] uppercase tracking-wide text-[#8b95a6]">{t.label}</div>
              <div className="mt-1.5 text-xl font-semibold font-mono" style={{ color: t.good ? "#4ade80" : "#f87171" }}>{t.value}</div>
            </div>
          ))}
        </div>

        <div className="flex gap-3 mt-8">
          <Link href="/blackboxops-os/agents" className="text-xs rounded-full px-4 py-2 border border-[#2a3040] hover:border-[#dba956] hover:text-[#dba956]">View live agent network →</Link>
          <Link href="/blackboxops-os/ert" className="text-xs rounded-full px-4 py-2 border border-[#2a3040] hover:border-[#dba956] hover:text-[#dba956]">ERT Center →</Link>
        </div>
      </div>
    </div>
  );
}
