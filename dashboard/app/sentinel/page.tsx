import { getSentinelLatest, getSentinelHistory } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";
import { HealthChart } from "@/components/HealthChart";

export default async function SentinelPage() {
  const [{ snapshot: s, services }, { snapshots: history }] = await Promise.all([
    getSentinelLatest(),
    getSentinelHistory(100),
  ]);
  const hasTempData = history.some((h) => h.cpu_temp_c !== null);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Sentinel</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Real psutil readings, taken live — not simulated. CPU temperature needs sudo, unavailable on this machine.
          </p>
        </div>
        <AutoRefresh intervalSeconds={15} />
      </div>

      {!s ? (
        <EmptyState>
          No snapshot yet. Run <code>python3 -m orchestrator.cli --sentinel-check</code>
        </EmptyState>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatTile label="Health Score" value={`${s.health_score}/100`} tone={s.health_score >= 80 ? "good" : s.health_score >= 50 ? "warn" : "bad"} />
            <StatTile label="Performance Score" value={`${s.performance_score}/100`} tone={s.performance_score >= 80 ? "good" : s.performance_score >= 50 ? "warn" : "bad"} />
            <StatTile label="CPU" value={`${s.cpu_percent}%`} hint={s.cpu_freq_mhz ? `${s.cpu_freq_mhz} MHz` : undefined} />
            <StatTile label="CPU Temp" value={s.cpu_temp_c !== null ? `${s.cpu_temp_c}°C` : "unavailable"} hint={s.cpu_temp_c === null ? "needs sudo" : undefined} />
            <StatTile label="RAM" value={`${s.ram_percent}%`} tone={s.ram_percent > 85 ? "warn" : "good"} />
            <StatTile label="Swap" value={`${s.swap_percent}%`} tone={s.swap_percent > 50 ? "warn" : "good"} />
            <StatTile label="Disk" value={`${s.disk_percent}%`} tone={s.disk_percent > 85 ? "warn" : "good"} />
            <StatTile label="Battery" value={s.battery_percent !== null ? `${s.battery_percent}%` : "n/a"} hint={s.battery_plugged ? "plugged in" : s.battery_percent !== null ? "on battery" : undefined} />
          </div>

          <div className="grid md:grid-cols-3 gap-4">
            <Card>
              <CardHeader title="CPU" subtitle={`last ${history.length} snapshots`} />
              <CardBody>
                <HealthChart snapshots={history} metric="cpu_percent" unit="%" domain={[0, 100]} />
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="RAM" subtitle={`last ${history.length} snapshots`} />
              <CardBody>
                <HealthChart snapshots={history} metric="ram_percent" unit="%" domain={[0, 100]} />
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="CPU Temperature" subtitle={hasTempData ? `last ${history.length} snapshots` : "unavailable on this machine"} />
              <CardBody>
                {hasTempData ? (
                  <HealthChart snapshots={history} metric="cpu_temp_c" unit="°C" />
                ) : (
                  <div className="text-sm text-[var(--muted-foreground)] py-8 text-center">
                    Needs <code>sudo powermetrics</code> — not available without elevated privileges on this machine.
                  </div>
                )}
              </CardBody>
            </Card>
          </div>

          <Card>
            <CardHeader title="Connectivity" />
            <CardBody className="flex flex-wrap gap-3">
              <Badge tone={s.internet_ok ? "good" : "bad"}>Internet {s.internet_ok ? "OK" : "DOWN"}</Badge>
              <Badge tone={s.ollama_ok ? "good" : "bad"}>Ollama {s.ollama_ok ? "OK" : "DOWN"}</Badge>
              <Badge tone={s.db_ok ? "good" : "bad"}>Database {s.db_ok ? "OK" : "DOWN"}</Badge>
              <Badge tone="neutral">{s.active_tasks} active tasks</Badge>
              <Badge tone={s.untriaged_errors > 0 ? "warn" : "good"}>{s.untriaged_errors} untriaged errors</Badge>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Services" />
            <CardBody className="grid md:grid-cols-2 gap-2 text-sm">
              {Object.entries(services).map(([name, status]) => (
                <div key={name} className="flex justify-between border-b border-[var(--border)] py-1.5">
                  <span className="capitalize">{name.replace("_", " ")}</span>
                  <span className="text-[var(--muted-foreground)]">{status}</span>
                </div>
              ))}
            </CardBody>
          </Card>

          <p className="text-xs text-[var(--muted-foreground)]">Snapshot taken {s.created_at}</p>
        </>
      )}
    </div>
  );
}
