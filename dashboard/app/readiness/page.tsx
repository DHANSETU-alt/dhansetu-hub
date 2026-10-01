import { getAgents, getBugs, getFailureAnalyses, getDecisions, getFinanceReport, getOverview } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile } from "@/components/ui";

// v3.4 error-proofing plan's readiness scorecard, made visible on the real
// dashboard. Per docs/v3.4/DHANSETU_REVENUE_READINESS_SCORECARD.md: most
// rows here require external verification (a curl, a screenshot, a
// production check) that this page cannot re-run live on every load --
// this table is a dated, manually-updated snapshot, not a fabricated
// live computation. The stat tiles above it (agent count, failure memory,
// approval queue, verified revenue) ARE live real-DB queries.

type ScoreRow = {
  category: string;
  score: number;
  status: string;
  evidence: string;
  blockers: string;
  next: string;
  agent: string;
};

const SCORECARD: ScoreRow[] = [
  { category: "Website Professionalism", score: 100, status: "Verified live", evidence: "Screenshot + curl, blackboxops.co.in, 2026-09-13", blockers: "None current", next: "Reconcile artifact-vs-real content drift as found", agent: "Website Implement Maker" },
  { category: "Product Range", score: 50, status: "Implemented, partial", evidence: "Business Planner + Offer Generator verified live; 8/10 modules roadmap-only", blockers: "8/10 advertised modules don't exist yet", next: "Pick the next single module to actually build", agent: "Website Implement Maker" },
  { category: "Offer Stack", score: 75, status: "Verified live, docs gap", evidence: "3-tier ladder verified via production curl + screenshot, 2026-09-13", blockers: "Guarantee/exclusions only implicit in UI copy", next: "Write explicit deliverables/exclusions one-pager", agent: "Strategy Maker" },
  { category: "Lead Capture", score: 50, status: "Implemented, not verified live", evidence: "Real leads/lead_events tables + insert_lead() exist", blockers: "No confirmed on-site-to-CRM bridge from blackboxops.co.in", next: "Build/confirm the real bridge", agent: "On-Site Bot" },
  { category: "Pricing/Payment Readiness", score: 100, status: "Verified live", evidence: "Real Razorpay checkout, server-computed tiers, verified end-to-end 2026-09-13", blockers: "None current", next: "Watch for first non-owner paid row", agent: "Money Calculator" },
  { category: "Trust/Legal Pages", score: 100, status: "Verified live", evidence: "/privacy, /terms, /refund-policy real and live", blockers: "None current", next: "Sync privacy page the moment GA goes live", agent: "Website Implement Maker" },
  { category: "SEO/AI Visibility", score: 100, status: "Verified live", evidence: "Search Console verified domain property; sitemap submitted 2026-09-13, status Success, 5 pages discovered (real screenshot)", blockers: "None current", next: "Monitor real indexing/impressions as they appear", agent: "Website Implement Maker" },
  { category: "Analytics/Tracking", score: 100, status: "Verified live", evidence: "Real GA4 property created + wired, real CSP connect-src bug found and fixed, verified via Realtime report showing a live test visit, 2026-09-13", blockers: "None current", next: "Watch real traffic/conversion data as outreach begins", agent: "Website Implement Maker" },
  { category: "Subscriber Acquisition", score: 50, status: "Implemented, unverified", evidence: "Real outreach templates drafted; one real send confirmed (WhatsApp, read receipts)", blockers: "No real payment resulted yet", next: "Send template 1 to the next named contact", agent: "Sales/Outreach" },
  { category: "Automation Reliability", score: 50, status: "Implemented, not fully supervised", evidence: "Real cron (*/5 * * * *) on blackboxops-os worker", blockers: "No systemd/launchd supervision for core orchestrator", next: "Stand up a supervised process, or document manual-restart as the model", agent: "24x7 Watchdog" },
  { category: "Security Readiness", score: 75, status: "Verified, real pass completed", evidence: "CSP/X-Frame/Referrer/Permissions headers added, CORS tightened to allowlist, 0 npm audit vulns both codebases, live checkout re-verified after both changes, 2026-09-13", blockers: "No full auth/session or rate-limiting review yet", next: "Review rate limiting on checkout/auth endpoints", agent: "Site Security Protector" },
  { category: "Bugfix/Failure Memory", score: 75, status: "Verified real, extension pending", evidence: "bugs/bug_events/patches/failure_analyses confirmed by schema read, 2026-09-13", blockers: "No agent_id backfill on old rows", next: "Backfill agent_id on new entries going forward", agent: "Bugfixer & Troubleshooting" },
];

function scoreTone(score: number): "good" | "warn" | "bad" {
  if (score >= 90) return "good";
  if (score >= 50) return "warn";
  return "bad";
}

export default async function ReadinessPage() {
  const [agentsRes, bugsRes, analysesRes, decisionsRes, financeRes, overviewRes] = await Promise.all([
    getAgents(),
    getBugs(),
    getFailureAnalyses(),
    getDecisions(50),
    getFinanceReport("monthly").catch(() => null),
    getOverview().catch(() => null),
  ]);

  const failureMemoryCount = bugsRes.bugs.length + analysesRes.analyses.length;
  // "Approval queue" is an honest approximation, not a formal unified
  // queue -- decisions.status has no real "pending" value (only
  // approved|rejected|revise), and bugs awaiting a human call sit at
  // patch_proposed/ceo_approved. See docs/v3.4/HIGH_RISK_APPROVAL_RULES.md §3.
  const decisionsNeedingReview = decisionsRes.decisions.filter((d) => d.status === "revise").length;
  const bugsAwaitingReview = bugsRes.bugs.filter((b) => b.status === "patch_proposed").length;
  const approvalQueueSize = decisionsNeedingReview + bugsAwaitingReview;

  const failedTasks = overviewRes?.recent_tasks.filter((t) => t.status === "failed") ?? [];

  const lowestScoring = [...SCORECARD].sort((a, b) => a.score - b.score)[0];
  const overallScore = Math.round(SCORECARD.reduce((sum, r) => sum + r.score, 0) / SCORECARD.length);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">DhanSetu Revenue Readiness</h1>
        <p className="text-sm text-[var(--muted-foreground)] mt-1">
          Failure-resistant with approval gates and evidence tracking -- not claimed error-proof. See{" "}
          <code>docs/v3.4/DHANSETU_REVENUE_READINESS_SCORECARD.md</code> for the full evidence trail behind every row below.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatTile label="Overall Readiness" value={`${overallScore}%`} tone={scoreTone(overallScore)} hint="Average of 12 scored categories" />
        <StatTile label="Real Agents" value={String(agentsRes.agents.length)} tone="good" hint="agents table, live query" />
        <StatTile label="Failure Memory" value={String(failureMemoryCount)} tone="neutral" hint="bugs + failure_analyses rows" />
        <StatTile label="Approval Queue" value={String(approvalQueueSize)} tone={approvalQueueSize > 0 ? "warn" : "good"} hint="revise decisions + patch_proposed bugs" />
        <StatTile
          label="Verified Revenue (30d)"
          value={financeRes ? `$${financeRes.revenue_usd.toFixed(2)}` : "—"}
          tone="neutral"
          hint="shakthi.db finance ledger, real numbers only"
        />
      </div>

      {failedTasks.length > 0 && (
        <Card>
          <CardHeader title="Failed Tasks" subtitle={`${failedTasks.length} real task(s) at status='failed' -- closest existing analog to \"blocked\" until the v3.4 lifecycle extension lands`} />
          <CardBody className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--muted-foreground)] border-b border-[var(--border)]">
                  <th className="px-5 py-2 font-medium">ID</th>
                  <th className="px-5 py-2 font-medium">Agent</th>
                  <th className="px-5 py-2 font-medium">Risk</th>
                  <th className="px-5 py-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {failedTasks.map((t) => (
                  <tr key={t.id} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-5 py-2 font-mono-num text-[var(--muted-foreground)]">#{t.id}</td>
                    <td className="px-5 py-2">{t.agent_id}</td>
                    <td className="px-5 py-2"><Badge tone={t.risk_level === "critical" ? "bad" : "neutral"}>{t.risk_level}</Badge></td>
                    <td className="px-5 py-2 text-xs text-[var(--muted-foreground)]">{t.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardBody>
        </Card>
      )}

      <Card>
        <CardHeader
          title="Next Best Action"
          subtitle={`Lowest-scoring category: ${lowestScoring.category} (${lowestScoring.score}%)`}
        />
        <CardBody>
          <p className="text-sm">{lowestScoring.next}</p>
          <p className="text-xs text-[var(--muted-foreground)] mt-1">Owner: {lowestScoring.agent}</p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Readiness Scorecard" subtitle="12 categories, dated 2026-09-13 -- see the doc for full evidence citations" />
        <CardBody className="p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--muted-foreground)] border-b border-[var(--border)]">
                <th className="px-5 py-2 font-medium">Category</th>
                <th className="px-5 py-2 font-medium">Score</th>
                <th className="px-5 py-2 font-medium">Status</th>
                <th className="px-5 py-2 font-medium">Blockers</th>
                <th className="px-5 py-2 font-medium">Next</th>
                <th className="px-5 py-2 font-medium">Agent</th>
              </tr>
            </thead>
            <tbody>
              {SCORECARD.map((row) => (
                <tr key={row.category} className="border-b border-[var(--border)] last:border-0 align-top">
                  <td className="px-5 py-2 font-medium">{row.category}</td>
                  <td className="px-5 py-2">
                    <Badge tone={scoreTone(row.score)}>{row.score}%</Badge>
                  </td>
                  <td className="px-5 py-2 text-xs">{row.status}</td>
                  <td className="px-5 py-2 text-xs text-[var(--muted-foreground)] max-w-[220px]">{row.blockers}</td>
                  <td className="px-5 py-2 text-xs max-w-[220px]">{row.next}</td>
                  <td className="px-5 py-2 text-xs text-[var(--muted-foreground)]">{row.agent}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>
    </div>
  );
}
