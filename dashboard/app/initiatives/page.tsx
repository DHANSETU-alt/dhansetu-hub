import { getInitiatives, type Initiative } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";
import { SmartCopyButton } from "@/components/SmartCopyButton";

export const dynamic = "force-dynamic";

const STATUS_TONE: Record<string, "good" | "warn" | "neutral"> = {
  running: "good",
  paused: "warn",
  done: "neutral",
};

function InitiativeCard({ init, label }: { init: Initiative; label: string }) {
  const remaining = init.milestones.filter((m) => !m.done);
  return (
    <Card key={init.id}>
      <CardHeader
        title={`${label} ${init.seq} — ${init.title}`}
        subtitle={
          init.artifact_url
            ? `Linked artifact: ${init.artifact_url}`
            : `${init.milestone_done}/${init.milestone_total} milestones done`
        }
        action={
          <div className="flex items-center gap-3">
            <span className="text-lg font-semibold font-mono-num text-[var(--ink)]">
              {init.percent_complete}%
            </span>
            <Badge tone={STATUS_TONE[init.status] ?? "neutral"}>{init.status}</Badge>
            <SmartCopyButton sourceId={init.id} sourceTitle={init.title} />
          </div>
        }
      />
      <CardBody>
        <div className="h-2 rounded-full bg-[var(--surface-2)] overflow-hidden mb-5">
          <div
            className="h-full rounded-full bg-[var(--local)] transition-all"
            style={{ width: `${init.percent_complete}%` }}
          />
        </div>

        {init.context?.cloned_from_title && (
          <p className="text-xs text-[var(--muted-foreground)] mb-3">
            Smart-copied from &ldquo;{init.context.cloned_from_title}&rdquo;
            {init.context.note ? ` — ${init.context.note}` : ""}
          </p>
        )}

        {init.artifact_url && (
          <a
            href={init.artifact_url}
            target="_blank"
            rel="noreferrer"
            className="inline-block text-xs text-[var(--local)] hover:underline mb-4"
          >
            Open linked artifact →
          </a>
        )}

        {/* Detailed analysis: exactly what's left, straight from the
            initiative's own unfinished milestones -- never a separately
            invented summary that could drift from the real checklist
            below it. Only shown for unfinished work; a done item has
            nothing left to analyze. */}
        {init.status !== "done" && remaining.length > 0 && (
          <div className="mb-4 rounded-md border border-[var(--warn)]/40 bg-[var(--warn)]/8 p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--warn)] font-semibold mb-1.5">
              What&rsquo;s left — {remaining.length} of {init.milestone_total}
            </div>
            <ul className="space-y-1 text-sm text-[var(--ink)]">
              {remaining.map((m) => (
                <li key={m.id} className="pl-3 -indent-3">
                  <span className="text-[var(--warn)]">▸ </span>
                  {m.title}
                </li>
              ))}
            </ul>
          </div>
        )}
        {init.status !== "done" && init.milestones.length === 0 && (
          <div className="mb-4 rounded-md border border-[var(--warn)]/40 bg-[var(--warn)]/8 p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--warn)] font-semibold">
              What&rsquo;s left — not yet broken into milestones
            </div>
            <p className="text-sm text-[var(--muted-foreground)] mt-1">
              Use <code>--milestone-add {init.id} &quot;TITLE&quot;</code> to record concrete next steps for this {label.toLowerCase()}.
            </p>
          </div>
        )}

        {init.milestones.length === 0 ? (
          <p className="text-xs text-[var(--muted-foreground)]">No milestones broken out yet.</p>
        ) : (
          <div className="space-y-1.5">
            {init.milestones.map((m) => (
              <div key={m.id} className="flex items-center gap-2.5 text-sm">
                <span
                  className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] shrink-0 ${
                    m.done
                      ? "bg-[var(--local-soft)] text-[var(--local)]"
                      : "border border-[var(--border)] text-transparent"
                  }`}
                >
                  {m.done ? "✓" : ""}
                </span>
                <span className={m.done ? "text-[var(--muted-foreground)] line-through" : "text-[var(--ink)]"}>
                  {m.title}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

// Finished work moves here -- one compact line each, not a full card. Kept
// visible (never hidden entirely -- the founder still owns this history)
// but out of the way of what actually needs attention, per the founder's
// own "unfinished on top, finished to the side" instruction.
function FinishedSidebar({ items }: { items: (Initiative & { trackLabel: string })[] }) {
  if (items.length === 0) {
    return (
      <Card>
        <CardHeader title="Finished" subtitle="Done work, out of the way" />
        <CardBody>
          <p className="text-xs text-[var(--muted-foreground)]">Nothing finished yet.</p>
        </CardBody>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader title="Finished" subtitle={`${items.length} done — real milestones, not a hand-picked count`} />
      <CardBody>
        <div className="space-y-2.5 max-h-[70vh] overflow-y-auto">
          {items.map((init) => (
            <div key={init.id} className="flex items-start gap-2 text-sm border-b border-[var(--border)] pb-2 last:border-0">
              <span className="mt-0.5 shrink-0 w-4 h-4 rounded-full flex items-center justify-center text-[10px] bg-[var(--local-soft)] text-[var(--local)]">✓</span>
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">{init.trackLabel} {init.seq}</div>
                <div className="text-[var(--ink)] leading-snug">{init.title}</div>
              </div>
            </div>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}

// Receives only unfinished (non-done) items -- done ones live in
// FinishedSidebar instead, per the founder's "unfinished on top, finished
// to the side" instruction. `totalCount` (including done) is passed
// separately so the empty state can tell "nothing exists yet" apart from
// "everything here is already finished" instead of conflating them.
function TrackColumn({
  heading,
  description,
  emptyHint,
  label,
  items,
  totalCount,
}: {
  heading: string;
  description: string;
  emptyHint: string;
  label: string;
  items: Initiative[];
  totalCount: number;
}) {
  const paused = items.filter((i) => i.status === "paused");
  return (
    <div className="space-y-4 flex-1 min-w-0">
      <div>
        <h2 className="text-base font-semibold">{heading}</h2>
        <p className="text-sm text-[var(--muted-foreground)] mt-1">{description}</p>
      </div>

      {items.length === 0 ? (
        <Card>
          <CardBody>
            <EmptyState>{totalCount > 0 ? `All ${totalCount} ${label.toLowerCase()}${totalCount === 1 ? "" : "s"} in this track are finished — see Finished.` : emptyHint}</EmptyState>
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-4">
          {items.map((init) => (
            <InitiativeCard key={init.id} init={init} label={label} />
          ))}
        </div>
      )}

      {paused.length > 0 && (
        <p className="text-xs text-[var(--warn)]">
          Paused, not neglected: {paused.map((i) => `${label} ${i.seq}`).join(", ")}
        </p>
      )}
    </div>
  );
}

export default async function InitiativesPage() {
  const result = await getInitiatives().catch(() => null);

  if (!result) {
    return (
      <Card>
        <CardHeader title="API unreachable" />
        <CardBody>
          <p className="text-sm text-[var(--muted-foreground)]">
            Could not reach the Shakthi API. Start it with{" "}
            <code className="text-[var(--ink)]">python3 -m orchestrator.api</code> in the shakthi-os directory, then reload.
          </p>
        </CardBody>
      </Card>
    );
  }

  const initiatives = result.initiatives;
  const tasks = initiatives.filter((i) => i.track === "task");
  const projects = initiatives.filter((i) => i.track === "project");
  const osTrack = initiatives.filter((i) => i.track === "os");

  const unfinishedTasks = tasks.filter((i) => i.status !== "done");
  const unfinishedProjects = projects.filter((i) => i.status !== "done");
  const unfinishedOs = osTrack.filter((i) => i.status !== "done");

  // Finished sidebar spans all three tracks together, newest-updated
  // first -- it's a "put it away" list, not something that needs the
  // same track separation the active work above does.
  const finished = [
    ...tasks.filter((i) => i.status === "done").map((i) => ({ ...i, trackLabel: "Task" })),
    ...projects.filter((i) => i.status === "done").map((i) => ({ ...i, trackLabel: "Project" })),
    ...osTrack.filter((i) => i.status === "done").map((i) => ({ ...i, trackLabel: "OS" })),
  ].sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Founder Tasks &amp; Projects</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Three separate tracks, never mixed: Tasks are real web-based work; Projects are big cross-platform
            software builds, now developed and verified Linux-first; OS is reserved exclusively for Shakthi_OS's own
            core upgrades. Percent complete is computed from real milestones below, never a hand-picked number.
            Unfinished work stays up top with what&rsquo;s actually left to do; finished work moves to the side.
          </p>
        </div>
        <AutoRefresh intervalSeconds={5} />
      </div>

      <div className="flex flex-col xl:flex-row gap-6 items-start">
        <div className="flex flex-col lg:flex-row gap-6 items-start flex-1 min-w-0">
          <TrackColumn
            heading="Tasks (web-based)"
            description="Task 1, Task 2, ... — dhansetuhub.in, blackboxops.co.in, PDF Studio, and the rest of the web work."
            emptyHint={`No tasks tracked yet. Use --initiative-add "TITLE" from the CLI to start Task 1.`}
            label="Task"
            items={unfinishedTasks}
            totalCount={tasks.length}
          />
          <TrackColumn
            heading="Projects (software dev)"
            description="Project 1, Project 2, ... — Linux-first software builds; other platform ports remain separate verified milestones."
            emptyHint={`No projects tracked yet. Use --initiative-add "TITLE" --initiative-track project from the CLI to start Project 1.`}
            label="Project"
            items={unfinishedProjects}
            totalCount={projects.length}
          />
          <TrackColumn
            heading="OS (Shakthi_OS core)"
            description="Special track, reserved only for Shakthi_OS's own core upgrades — not customer-facing apps or web work."
            emptyHint={`No OS-track items yet. Use --initiative-add "TITLE" --initiative-track os from the CLI to start OS 1.`}
            label="OS"
            items={unfinishedOs}
            totalCount={osTrack.length}
          />
        </div>

        <div className="w-full xl:w-80 shrink-0">
          <FinishedSidebar items={finished} />
        </div>
      </div>
    </div>
  );
}
