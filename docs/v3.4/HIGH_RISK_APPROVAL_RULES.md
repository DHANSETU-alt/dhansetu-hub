# High-Risk Approval Rules — v3.4

Date: 2026-09-13
Real backing confirmed by direct schema read this session.

## 0. Two real gates already exist — use them, don't invent a third

**Gate A — general task approval, real:** the `decisions` table.

```sql
CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER REFERENCES tasks(id),
  business_id INTEGER REFERENCES businesses(id),
  goal TEXT NOT NULL,
  status TEXT NOT NULL,          -- approved | rejected | revise
  priority_score INTEGER,        -- 1-10
  risk_score INTEGER,            -- 1-10
  business_impact_score INTEGER, -- 1-10
  reason TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

`ceo.yaml` is the real agent whose contract is to populate this table —
it already scores risk and business impact before a task can proceed.

**Gate B — bugfix-specific approval, real:** `bugs.status` already has
`ceo_approved`/`ceo_rejected` as first-class states, logged into
`bug_events` (`event_type = 'ceo_approved' | 'ceo_rejected'`).

**Gate C — Claude Code session actions, real but different in kind:**
when a Claude Code session (like this one) performs a DNS change,
secret rotation, or production deploy directly, the real approval
mechanism today is **explicit chat confirmation with the founder before
the action**, not a `decisions` row. This session's own pattern this same
day — asking before submitting the Search Console sitemap form, asking
which pricing-tier structure to build before wiring real Razorpay charges
to it — *is* Gate C in practice. Document it as real, rather than
pretending Gate A covers actions a database-driven agent pipeline never
actually took.

## 1. Risk categories → real gate mapping

| Category | Founder's risk level | Real gate today |
|---|---|---|
| Payment actions | HIGH | Gate C (session-level chat confirmation) for one-off changes to pricing/checkout code; real server-side amount computation (never client-trusted) is the runtime safeguard once code is live |
| Deleting emails/files/data | HIGH | No dedicated gate confirmed to exist yet — treat as Gate C only, always |
| Bulk outreach/messaging | HIGH | No automated send capability exists in this session's scope — outreach is drafted, never auto-sent (confirmed: no send tool was used for the outreach templates this session) |
| DNS/domain changes | HIGH | Gate C. Real constraint: the current Cloudflare API token used this session has `zone:read` only, not DNS-write — so most DNS changes are *structurally* blocked today, not just gated by policy |
| Auth/secret changes | HIGH | Gate C. `wrangler secret put` was used this session only after explicit real production evidence (empty `wrangler secret list`) justified it |
| Production deploy | HIGH | Gate C, always — every deploy this session was preceded by typecheck+test+build+local-visual-check, and followed by a real production curl/screenshot verification |
| Security/firewall changes | HIGH | No real gate confirmed for this specific category — treat as Gate C |
| Form handling / lead storage | MEDIUM | Real `leads` table exists; verify writes, don't just assume they happen (see readiness scorecard row 4) |
| Analytics scripts | MEDIUM | Real: this session added GA4 as an off-by-default scaffold specifically so no live tracking script goes out without a real ID and a synced privacy-page update |
| Pricing page changes | MEDIUM/HIGH boundary | Treated as HIGH in practice this session (founder consulted before restructuring tiers) since it directly changes what customers are charged |
| Routing | MEDIUM | No incidents this session |
| Copy/UI/docs/local dashboard | LOW | Proceeds automatically — this is most of what this session did without asking |

## 2. Rule, restated plainly

- **LOW** proceeds automatically. (Copy, layout, docs, local previews,
  non-destructive checks.)
- **MEDIUM** proceeds but must be verified — typecheck/test/build locally,
  or a real query confirming the data landed where expected.
- **HIGH** requires approval before execution — either a real `decisions`/
  `bugs` row (agent-driven work) or explicit chat confirmation (Claude
  Code session work). Never silently downgraded to MEDIUM because the
  action "seemed small."

## 3. What this document does NOT claim

It does not claim a unified, single approval queue exists across both
agent-driven work (`decisions`/`bugs`) and session-driven work (chat
confirmation) — those are two real, separate mechanisms today. Unifying
them into one dashboard-visible "high-risk approval queue" (as the
founder's dashboard-features ask requests) is a real, buildable next step,
not something already done.
