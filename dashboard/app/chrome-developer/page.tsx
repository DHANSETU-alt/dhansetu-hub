import { getWebsiteReviews } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

function avg(nums: (number | null)[]) {
  const vals = nums.filter((n): n is number => n !== null);
  if (!vals.length) return null;
  return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
}

export default async function ChromeDeveloperPage() {
  const { reviews } = await getWebsiteReviews(50);
  const completed = reviews.filter((r) => r.status === "completed");
  const avgSeo = avg(completed.map((r) => r.seo_score));
  const avgConversion = avg(completed.map((r) => r.conversion_score));
  const readyCount = completed.filter((r) => r.deployment_ready).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Chrome Developer Bot</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Website Review, SEO Score, and Conversion Score in one page — one review pipeline, not three separate
            views of the same run. Conversion Score and browser-driven checks (console errors, real load time,
            mobile overflow) come from an actual headless Chromium pass, not just HTML parsing. Runs automatically
            after every Website Builder site.
          </p>
        </div>
        <AutoRefresh intervalSeconds={30} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Avg SEO Score" value={avgSeo !== null ? `${avgSeo}/100` : "—"} tone={avgSeo !== null && avgSeo < 70 ? "warn" : "good"} />
        <StatTile label="Avg Conversion Score" value={avgConversion !== null ? `${avgConversion}/100` : "—"} tone={avgConversion !== null && avgConversion < 70 ? "warn" : "good"} />
        <StatTile label="Reviews Run" value={String(reviews.length)} />
        <StatTile label="Deployment Ready" value={`${readyCount}/${completed.length}`} tone={readyCount === completed.length && completed.length > 0 ? "good" : "warn"} />
      </div>

      <Card>
        <CardHeader title="Website Reviews" subtitle={`${reviews.length} run(s)`} />
        <CardBody className="p-0">
          {reviews.length === 0 ? (
            <EmptyState>
              No reviews yet. Run <code>python3 -m orchestrator.cli --website-review https://example.com</code>
            </EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {reviews.map((r) => (
                <div key={r.id} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium truncate max-w-[40ch]">#{r.id} · {r.url}</span>
                    <div className="flex items-center gap-2">
                      <Badge tone={r.status === "completed" ? "good" : r.status === "failed" ? "bad" : "warn"}>{r.status}</Badge>
                      {r.status === "completed" && (
                        <Badge tone={r.deployment_ready ? "good" : "warn"}>{r.deployment_ready ? "ready" : "not ready"}</Badge>
                      )}
                    </div>
                  </div>
                  <div className="mt-1.5 flex items-center gap-4 text-xs text-[var(--muted-foreground)]">
                    <span>SEO {r.seo_score ?? "—"}</span>
                    <span>Conversion {r.conversion_score ?? "—"}</span>
                    <span>UI {r.ui_score ?? "—"}</span>
                    <span>{r.findings_count} findings</span>
                    <span className="font-mono-num">{r.completed_at || r.created_at}</span>
                  </div>
                  {r.summary && <p className="mt-1.5 text-xs text-[var(--muted-foreground)] max-w-[70ch]">{r.summary}</p>}
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
