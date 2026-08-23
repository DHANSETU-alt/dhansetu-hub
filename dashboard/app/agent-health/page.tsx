import { ComingSoon } from "@/components/ui";

export default function AgentHealthPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Agent Health Monitor</h1>
      <ComingSoon
        title="Agent Health Monitor"
        note="Per-agent success/failure rate, average latency, and escalation rate over time. The Telegram /health command and report_generators.agent_health_report_text() already compute a version of this — this page would visualize that same data with trend charts, not built yet."
      />
    </div>
  );
}
