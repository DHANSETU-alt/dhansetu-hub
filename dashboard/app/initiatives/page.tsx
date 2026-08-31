import { getInitiatives, type Initiative } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

export const dynamic = "force-dynamic";

const STATUS_TONE: Record<string, "good" | "warn" | "neutral"> = {
  running: "good",
  paused: "warn",
  done: "neutral",
};

function InitiativeCard({ init, label }: { init: Initiative; label: string }) {
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

function TrackColumn({
  heading,
  description,
  emptyHint,
  label,
  items,
}: {
  heading: string;
  description: string;
  emptyHint: string;
  label: string;
  items: Initiative[];
}) {
  const running = items.filter((i) => i.status === "running");
  return (
    <div className="space-y-4 flex-1 min-w-0">
      <div>
        <h2 className="text-base font-semibold">{heading}</h2>
        <p className="text-sm text-[var(--muted-foreground)] mt-1">{description}</p>
      </div>

      {items.length === 0 ? (
        <Card>
          <CardBody>
            <EmptyState>{emptyHint}</EmptyState>
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-4">
          {items.map((init) => (
            <InitiativeCard key={init.id} init={init} label={label} />
          ))}
        </div>
      )}

      {running.length > 0 && (
        <p className="text-xs text-[var(--muted-foreground)]">
          Currently running: {running.map((i) => `${label} ${i.seq}`).join(", ")}
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
  const tasks = initiatives.filter((i) => i.track !== "project");
  const projects = initiatives.filter((i) => i.track === "project");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Founder Tasks &amp; Projects</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Two separate tracks, never mixed: Tasks are real web-based work; Projects are big cross-platform
            software builds (Mac, Windows, Linux, iOS, Android). Percent complete is computed from real milestones
            below, never a hand-picked number.
          </p>
        </div>
        <AutoRefresh intervalSeconds={20} />
      </div>

      <div className="flex flex-col lg:flex-row gap-6 items-start">
        <TrackColumn
          heading="Tasks (web-based)"
          description="Task 1, Task 2, ... — dhansetuhub.in, blackboxops.co.in, PDF Studio, and the rest of the web work."
          emptyHint={`No tasks tracked yet. Use --initiative-add "TITLE" from the CLI to start Task 1.`}
          label="Task"
          items={tasks}
        />
        <TrackColumn
          heading="Projects (software dev)"
          description="Project 1, Project 2, ... — big cross-platform builds: Mac, Windows, Linux, iOS, Android."
          emptyHint={`No projects tracked yet. Use --initiative-add "TITLE" --initiative-track project from the CLI to start Project 1.`}
          label="Project"
          items={projects}
        />
      </div>
    </div>
  );
}
