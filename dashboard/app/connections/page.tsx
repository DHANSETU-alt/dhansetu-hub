import { getHealth, getMacRuntime } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";
import Link from "next/link";

export default async function Connections() {
  const [health, runtime] = await Promise.all([getHealth().catch(() => null), getMacRuntime().catch(() => null)]);
  return <div className="space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-4"><h1 className="text-2xl font-semibold">Connections & readiness</h1><AutoRefresh intervalSeconds={1}/></div>
    <p className="text-[var(--muted-foreground)]">Local API evidence for this installation. A reachable endpoint does not prove successful task execution.</p>
    <div className="grid gap-5 md:grid-cols-2">
      <Card><CardHeader title="Orchestrator API" action={<Badge tone={health ? "good" : "bad"}>{health ? "REACHABLE" : "UNAVAILABLE"}</Badge>}/><CardBody>Database: {health ? (health.db_ok ? "responding" : "check failed") : "unknown"}<p>Execution permission: {health ? (health.allow_exec ? "enabled" : "disabled by existing policy") : "unknown"}</p><p>Dry run: {health ? String(health.dry_run) : "unknown"}</p></CardBody></Card>
      <Card><CardHeader title="Hardware telemetry" action={<Badge tone={runtime ? "local" : "bad"}>{runtime ? "LOCAL SAMPLE" : "UNAVAILABLE"}</Badge>}/><CardBody>{runtime ? <><p>Host: {runtime.hostname}</p><p>Sample: {new Date(runtime.sampled_at * 1000).toISOString()}</p><p>GPU: {runtime.gpu.state} · {runtime.gpu.name || runtime.gpu.reason}</p></> : "No current sample. Check the local API service."}</CardBody></Card>
      <Card><CardHeader title="Local model provider" action={<Badge tone="warn">CONFIGURATION ONLY</Badge>}/><CardBody><p>{health?.ollama_host || "API unavailable"}</p><p>A configured address is not an inference test. Check agent status and a completed task before relying on model execution.</p><Link className="underline" href="/agent-health">Inspect agent health</Link></CardBody></Card>
      <Card><CardHeader title="External integrations" action={<Badge tone="warn">VERIFICATION REQUIRED</Badge>}/><CardBody><p>Provider credentials, payments and remote execution retain their existing controls. This page does not infer connectivity or change permissions.</p><div className="flex flex-wrap gap-4 mt-4"><Link className="underline" href="/payments">Payment evidence</Link><Link className="underline" href="/costs">Usage ledger</Link><Link className="underline" href="/security">Security status</Link></div></CardBody></Card>
    </div>
  </div>;
}
