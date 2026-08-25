import Link from "next/link";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { getAgents, getDhansetuCourses, getDhansetuContentQueue, getDhansetuLinks } from "@/lib/api";

export const dynamic = "force-dynamic";

const SQUAD = "Dhansetu AI";
const CONTENT_TYPE_LABEL: Record<string, string> = {
  visual_prompt: "Visual prompt",
  reel_script: "Reel script",
  instagram_post: "Instagram caption",
};

export default async function DhansetuAiPage() {
  const [agentsRes, coursesRes, queueRes, linksRes] = await Promise.all([
    getAgents(),
    getDhansetuCourses(),
    getDhansetuContentQueue(),
    getDhansetuLinks(),
  ]);

  const squadAgents = agentsRes.agents.filter((a) => a.squad === SQUAD);
  const pa = agentsRes.agents.find((a) => a.id === "pa_angella");
  const courses = coursesRes.courses;
  const queue = queueRes.items;
  const readyToPost = queue.filter((i) => i.status === "ready_to_post");
  const activeLinks = linksRes.links.filter((l) => l.active);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Dhansetu AI</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Course-selling branch, kept separate from Sales/Marketing on purpose. PA Angella refines the founder&apos;s
            requests for the CEO; the Assistant Manager and 4 specialists below handle course drafting, visual
            prompts, reel scripts, and post captions — in Gujarati by default.
          </p>
        </div>
        <Badge tone="local">Instagram only, for now</Badge>
      </div>

      <div className="rounded-xl border p-4 text-sm" style={{ borderColor: "color-mix(in srgb, var(--warn) 40%, var(--border))", background: "color-mix(in srgb, var(--warn) 6%, var(--surface))" }}>
        <span className="font-semibold" style={{ color: "var(--warn)" }}>Honest scope, stated plainly: </span>
        <span className="text-[var(--muted-foreground)]">
          no image/video generation is connected anywhere in this project — the Prompt Writer and Reel Scripter produce
          real text (a prompt, a script), never a rendered image or video. No Instagram/Meta API is connected either —
          &quot;ready to post&quot; below is a real status, not an actual publish. A human posts it today, or a real
          posting integration gets wired in later.
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Courses" value={String(courses.length)} hint={`${courses.filter((c) => c.status === "ready").length} ready`} />
        <StatTile label="Content drafted" value={String(queue.length)} />
        <StatTile label="Ready to post" value={String(readyToPost.length)} tone={readyToPost.length > 0 ? "good" : "neutral"} />
        <StatTile label="Bio links live" value={String(activeLinks.length)} />
      </div>

      <Card>
        <CardHeader title="The branch" subtitle="PA Angella (top-level) + the Dhansetu AI squad — separate from Sales/Marketing" />
        <CardBody>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {pa && (
              <div className="rounded-lg border border-[var(--border)] p-3">
                <div className="text-sm font-medium">{pa.name}</div>
                <div className="text-xs text-[var(--muted-foreground)] mt-0.5">Founder ↔ CEO relay</div>
              </div>
            )}
            {squadAgents.map((a) => (
              <div key={a.id} className="rounded-lg border border-[var(--border)] p-3">
                <div className="text-sm font-medium">{a.name}</div>
                <div className="text-xs text-[var(--muted-foreground)] mt-0.5">
                  {a.id === "dhansetu_manager" ? "Assistant Manager (hub)" : "Specialist"}
                </div>
              </div>
            ))}
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Courses" subtitle="Drafted from titles — manual entry or pulled from a Google Sheet" />
        <CardBody>
          {courses.length === 0 ? (
            <EmptyState>No courses yet. Use --dhansetu-ingest-sheet or add one manually to get started.</EmptyState>
          ) : (
            <div className="space-y-2">
              {courses.map((c) => (
                <div key={c.id} className="flex items-center justify-between rounded-lg border border-[var(--border)] px-3 py-2">
                  <div>
                    <div className="text-sm font-medium">{c.title}</div>
                    <div className="text-xs text-[var(--muted-foreground)] mt-0.5">{c.language.toUpperCase()} · {c.source || "manual"}</div>
                  </div>
                  <Badge tone={c.status === "ready" ? "good" : c.status === "published" ? "local" : "neutral"}>{c.status}</Badge>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Content queue" subtitle="Visual prompts, reel scripts, and captions — text only, see the note above" />
        <CardBody>
          {queue.length === 0 ? (
            <EmptyState>Nothing drafted yet.</EmptyState>
          ) : (
            <div className="space-y-2">
              {queue.slice(0, 10).map((i) => (
                <div key={i.id} className="rounded-lg border border-[var(--border)] px-3 py-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono uppercase tracking-wide text-[var(--muted-foreground)]">
                      {CONTENT_TYPE_LABEL[i.content_type] || i.content_type}
                    </span>
                    <Badge tone={i.status === "ready_to_post" ? "good" : "neutral"}>{i.status}</Badge>
                  </div>
                  <p className="text-sm mt-1.5 line-clamp-2">{i.content}</p>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Bio link page"
          subtitle="The real, public Instagram link-tree page"
          action={<Link href="/dhansetu-ai/links" className="text-xs font-mono text-[var(--local)] hover:underline">View live page →</Link>}
        />
        <CardBody>
          {activeLinks.length === 0 ? (
            <EmptyState>No links added yet — use --dhansetu-add-link to add real ones. The public page states this honestly, no placeholders.</EmptyState>
          ) : (
            <div className="space-y-1.5">
              {activeLinks.map((l) => (
                <div key={l.id} className="text-sm flex items-center gap-2">
                  <span className="font-medium">{l.title}</span>
                  <span className="text-[var(--muted-foreground)] text-xs truncate">{l.url}</span>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
