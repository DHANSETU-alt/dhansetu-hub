import { getVoiceRecent } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";
import { JarvisVoiceControl } from "@/components/JarvisVoiceControl";

const IDENTITY_TONE: Record<string, "good" | "warn" | "neutral"> = { owner: "good", family: "neutral", guest: "warn" };

export default async function VoiceCommanderPage() {
  const { commands } = await getVoiceRecent();
  const denied = commands.filter((c) => c.denied_reason);
  const completed = commands.length - denied.length;
  const languages = new Set(commands.map((c) => c.detected_language).filter(Boolean));
  const completionRate = commands.length ? Math.round((completed / commands.length) * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2"><Badge tone="local">Jarvis Interface</Badge><Badge tone="neutral">Local control plane</Badge></div>
          <h1 className="text-2xl font-semibold tracking-tight">Voice Commander</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted-foreground)]">Speak naturally in English, Hindi, or Gujarati. Jarvis converts loose conversation into a structured OS request, checks identity and risk, routes the request, and speaks back the result.</p>
        </div>
        <AutoRefresh intervalSeconds={15} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Commands Logged" value={String(commands.length)} hint="Stored voice audit records" />
        <StatTile label="Completed" value={String(completed)} hint={`${completionRate}% of logged requests`} tone={completed ? "good" : "neutral"} />
        <StatTile label="Permission Denied" value={String(denied.length)} hint="Blocked by identity policy" tone={denied.length ? "warn" : "good"} />
        <StatTile
          label="Languages Detected"
          value={String(languages.size)}
          hint={languages.size ? Array.from(languages).join(" · ").toUpperCase() : "No detected speech yet"}
        />
      </div>

      <JarvisVoiceControl />

      <div className="grid gap-4 lg:grid-cols-[1.35fr_1fr]">
        <Card>
          <CardHeader title="How Jarvis handles your request" subtitle="Policy-controlled routing; risky actions do not bypass approval" />
          <CardBody>
            <div className="grid gap-2 sm:grid-cols-5">
              {[
                ["01", "Hear", "Browser microphone"],
                ["02", "Interpret", "Prompt Master"],
                ["03", "Authorize", "Identity + risk gate"],
                ["04", "Route", "SHAKTHI agent"],
                ["05", "Respond", "Voice + screen"],
              ].map(([number, title, detail]) => (
                <div key={number} className="rounded-lg border border-[var(--border)] bg-black/20 p-3">
                  <div className="font-mono text-[10px] text-[var(--local)]">{number}</div>
                  <div className="mt-2 text-xs font-semibold">{title}</div>
                  <div className="mt-1 text-[10px] leading-4 text-[var(--muted-foreground)]">{detail}</div>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Current access boundary" subtitle="What this browser session can do" />
          <CardBody>
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between"><span className="text-[var(--muted-foreground)]">Session identity</span><Badge tone="warn">Guest</Badge></div>
              <div className="flex items-center justify-between"><span className="text-[var(--muted-foreground)]">Read-only safe requests</span><Badge tone="good">Available</Badge></div>
              <div className="flex items-center justify-between"><span className="text-[var(--muted-foreground)]">Sensitive OS actions</span><Badge tone="bad">Restricted</Badge></div>
              <p className="border-t border-[var(--border)] pt-3 leading-5 text-[var(--muted-foreground)]">Owner authentication is not configured for this browser voice route. Denials below are security-policy outcomes, not system failures.</p>
            </div>
          </CardBody>
        </Card>
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
                <div key={c.id} className="px-4 py-4 sm:px-5">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">Input transcript</div>
                      <span className="block text-sm leading-5">&quot;{c.raw_transcript}&quot;</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge tone={IDENTITY_TONE[c.identity] ?? "neutral"}>{c.identity}</Badge>
                      {c.denied_reason ? (
                        <Badge tone="bad">denied</Badge>
                      ) : (
                        <Badge tone="good">ok</Badge>
                      )}
                    </div>
                  </div>
                  <div className="mt-3 grid gap-2 rounded-md border border-[var(--border)] bg-black/20 p-3 text-xs text-[var(--muted-foreground)] sm:grid-cols-3">
                    <span><span className="block text-[9px] uppercase tracking-wider">Route</span><span className="text-[var(--ink)]">{c.routed_agent ?? "—"}/{c.routed_action ?? "—"}</span></span>
                    {c.detected_language && <span>lang: {c.detected_language} ({Math.round((c.language_confidence ?? 0) * 100)}%)</span>}
                    <span><span className="block text-[9px] uppercase tracking-wider">Recorded</span><span className="font-mono-num text-[var(--ink)]">{c.created_at}</span></span>
                  </div>
                  {c.denied_reason && <p className="mt-2 text-xs text-[var(--bad)]">Policy decision: {c.denied_reason}</p>}
                  {c.result_summary && <p className="mt-2 rounded-md bg-[var(--surface-2)] px-3 py-2 text-xs leading-5 text-[var(--muted-foreground)]"><span className="font-semibold text-[var(--ink)]">Jarvis response:</span> {c.result_summary}</p>}
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
