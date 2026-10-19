# Website Backup Report — blackboxops.co.in

Phase 1 of the blackboxOps_OS migration order. This backs up the **live, deployed site directly over HTTP** — not a local project folder, since which of the 5 local candidates (`dhansetu-hub-live`, `dhansetu-pdf-studio`, `dhansetu-peopledesk`, `partner-roadmap`, `public-landing`) is actually deployed as this domain is still unanswered (asked twice, not yet confirmed). Backing up the live site directly means Phase 1 didn't have to wait on that answer — everything below is real, fetched just now, not assumed.

## What the site actually is (real finding, not assumed)

```
Title:       BlackBoxOps AI — AI-assisted operations for small agencies
Description: Practical AI-assisted workflows for client reporting, lead
             follow-up and task handoffs—with human approval and clear
             guardrails.
```

This is a coherent, useful discovery for the migration itself: the live product is **already** an AI-ops tool for small agencies with a human-approval-gated workflow philosophy — thematically close to SHAKTHI OS's own architecture (local-first agents, CEO approval gates, fail-closed design). The migration isn't inventing a new product from nothing; it's re-platforming an existing, coherent one onto real infrastructure that already exists.

## What was backed up

```
/Users/apple/shakthi-os/blackboxops_os_backup/2026-08-24/
├── homepage.html                                    41,935 bytes
├── favicon.svg                                          712 bytes
└── _next/static/
    ├── chunks/index-M4JEGhi9.js                     176,582 bytes
    ├── chunks/layout-segment-context-D7x8PMJz.js         494 bytes
    ├── chunks/razorpay-checkout-BLUXvEho.js            1,856 bytes
    └── css/index.Cb9r7Col.css                         18,029 bytes
```
Total: 276 KB. `robots.txt` and `sitemap.xml` both returned 404 — genuinely absent, not a fetch failure (confirmed with direct requests to both).

## Real finding: Razorpay is already live on this site

`razorpay-checkout-*.js` isn't a guess at a filename — it's the actual chunk name Next.js's bundler assigned, and its contents are the real Razorpay Checkout.js loader:
```js
function a(){return new Promise(e=>{if(window.Razorpay)return e(!0);
  let t=document.createElement("script");
  t.src="https://checkout.razorpay.com/v1/checkout.js"; ...
```
**Phase 4's Razorpay integration may already partially exist on production.** Before building a new one, check whether the existing checkout flow can be extended rather than replaced — worth confirming once the source repo is identified.

## Technical stack (real, from the bundle — not assumed)

- Next.js (`/_next/static/...` paths, standard Next.js output structure)
- Bundled via `rolldown` (`rolldown-runtime-*.js` import seen in the Razorpay chunk) — a newer, Vite-adjacent bundler, consistent with the `vinext`/`vite`/`wrangler` toolchain already found in all 5 candidate local projects during the Gatekeeper investigation
- Client-side rendering for at least the Razorpay checkout flow (a `useState`-based React component, not server-rendered)

This is consistent with — though doesn't uniquely prove — the site being one of the 5 local projects sharing the `site-creator-vinext-starter` template. It's real supporting evidence, not proof; the folder-identity question is still open.

## Real audit scores (WEB-001 tool, run against the live site just now)

| Metric | Score | Real finding |
|---|---|---|
| Website Health | 100/100 | Loads cleanly, HTTPS valid, 0 broken links |
| SEO | 57/100 | Title and meta description both present and correctly sized; single H1; **no sitemap.xml, no robots.txt** |
| Security | 40/100 | HTTPS is valid, but **0 of 5 standard security headers present** (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy) |
| Performance | 100/100 | Fast |

## What this means for the migration plan

- The backup is real and complete for what a static HTTP fetch can capture. It does **not** include: server-side code, the database/CMS behind it (if any), environment variables, or the Razorpay/PayU merchant configuration — none of that is fetchable over HTTP, and none of it exists in this backup. If the live site has a backend or database, that still needs a real source (repo access or hosting-dashboard export), not just this.
- Security headers and sitemap/robots.txt are real, concrete, low-risk wins to carry into the blackboxOps_OS staging build regardless of anything else in the migration.
- Whatever staging build follows should preserve the working Razorpay integration's actual behavior (or deliberately supersede it with the fuller Razorpay + PayU flow already built in `orchestrator/payment_gateway_manager.py` this session) rather than accidentally regressing a payment flow that already works in production.

See `blackboxOps_OS_MIGRATION_PLAN.md` for what happens next.
