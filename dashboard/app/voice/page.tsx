import { getVoiceRecent } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

const IDENTITY_TONE: Record<string, "good" | "warn" | "neutral"> = { owner: "good", family: "neutral", guest: "warn" };

export default async function VoiceCommanderPage() {
  const { commands } = await getVoiceRecent();
  const denied = commands.filter((c) => c.denied_reason);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Voice Commander</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Mic → local Whisper STT → intent routing → CEO review (risky commands only) → Owner/Family/Guest permission → agent.
          </p>
        </div>
        <AutoRefresh intervalSeconds={15} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatTile label="Commands Logged" value={String(commands.length)} />
        <StatTile label="Denied" value={String(denied.length)} tone={denied.length ? "warn" : "good"} />
        <StatTile
          label="Languages Detected"
          value={String(new Set(commands.map((c) => c.detected_language).filter(Boolean)).size)}
        />
      </div>

      <Card>
        <CardHeader title="Recent Commands" subtitle={`${commands.length} shown, most recent first`} />
        <CardBody className="p-0">
          {commands.length === 0 ? (
            <EmptyState>
              None yet. Run <code>python3 -m orchestrator.cli --voice-listen</code> (grants mic permission on first use).
            </EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {commands.map((c) => (
                <div key={c.id} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm max-w-[55ch] truncate">&quot;{c.raw_transcript}&quot;</span>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge tone={IDENTITY_TONE[c.identity] ?? "neutral"}>{c.identity}</Badge>
                      {c.denied_reason ? (
                        <Badge tone="bad">denied</Badge>
                      ) : (
                        <Badge tone="good">ok</Badge>
                      )}
                    </div>
                  </div>
                  <div className="mt-1 flex items-center gap-3 text-xs text-[var(--muted-foreground)]">
                    <span>{c.routed_agent ?? "—"}/{c.routed_action ?? "—"}</span>
                    {c.detected_language && <span>lang: {c.detected_language} ({Math.round((c.language_confidence ?? 0) * 100)}%)</span>}
                    {c.denied_reason && <span className="text-[var(--bad)]">{c.denied_reason}</span>}
                    <span className="font-mono-num">{c.created_at}</span>
                  </div>
                  {c.result_summary && <p className="mt-1 text-xs text-[var(--muted-foreground)]">→ {c.result_summary}</p>}
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
