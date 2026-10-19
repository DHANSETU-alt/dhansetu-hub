# DhanSetu Hub Mission Tasks

## Phase 0 — Preserve and Baseline

- [x] Identify canonical parent repository, nested repository, branch, HEAD, remote, and dirty state.
- [x] Identify current database path and run integrity check.
- [x] Run initial Python tests, frontend lint, production build, and Git diff check.
- [x] Identify external SSD hardware and mount incompatibility without modifying it.
- [x] Identify active legacy launchd/cron automation.
- [ ] Create encrypted SSD archive of protected repository/config/data and a secret-free manifest.
- [ ] Sample-restore repository, database, uploads, and configuration into an isolated restore-test directory.
- [ ] Record database table-level inventory and protected-data classifications without exposing PII.

### Checkpoint 0

- [ ] Backup can be listed and sample-restored.
- [ ] Dirty working state is recoverable.
- [ ] Exact quarantine candidates are reviewed against the archive manifest.

## Phase 1 — Critical Security and Authority

- [x] Add failing tests proving clients cannot submit Razorpay secrets or arbitrary amounts/products.
- [x] Move payment order creation and verification to server-only credentials and fixed product IDs (₹149/₹399 one-time tiers).
- [ ] Add idempotent verified-payment-to-entitlement tests, including retries and refunds/reversals.
- [ ] Remove inline bot credentials from cron/process arguments and rotate the exposed credential.
- [ ] Inventory Google sign-in/session implementation and close auth/CSRF/role gaps with browser evidence.
- [ ] Protect Resume AI prompts, tax documents, founder reports, and partner data with server authorization.

### Checkpoint 1

- [ ] Python tests, frontend lint, type checking, and production build pass.
- [ ] Security-focused tests pass with no client-controlled payment authority.
- [ ] No secret appears in Git diff, browser bundle, process list, or logs.

## Phase 2 — Canonical DhanSetu Product Shell

- [ ] Merge retained static DhanSetu routes/assets from nested `dhansetu-web` into the canonical app.
- [ ] Establish DhanSetu-only navigation, terminology, product catalog, and route map behind safe flags.
- [ ] Replace remote build-time fonts with reliable local/system typography.
- [ ] Add root `AGENTS.md` and `CODEX_MAINTENANCE.md`; archive obsolete agent/OS instructions after backup.
- [ ] Add privacy, terms, deletion, partner disclosure, and product-limitations pages aligned with behavior.

### Checkpoint 2

- [ ] One documented development startup path works.
- [ ] Desktop and mobile product shell passes browser accessibility and responsive checks.
- [ ] Existing DhanSetu routes remain compatible.

## Phase 3 — Product Vertical Slices

- [ ] SmartBudget onboarding, transactions, CSV duplicate protection, dashboard, recurring items, goals, and explainable LeakShield.
- [ ] Versioned salaried tax estimator with official-source fixtures and unsupported-case handling.
- [ ] GST purchase-register/GSTR-2B reconciliation with review-only findings.
- [ ] Resume upload/extraction/edit/export and entitlement-safe private prompts.
- [ ] Partner applications, referral attribution, held/approved/reversed commission ledger, and audit trail.

### Checkpoint 3

- [ ] Each product has focused unit/integration/browser tests and honest empty/error states.
- [ ] Financial conclusions come from deterministic code with version/source metadata.

## Phase 4 — Founder Command Center

- [ ] Define shared metric dictionary and verified event sources.
- [ ] Implement Today and Money workspaces with drill-through and freshness/status labels.
- [ ] Implement Customers, Products, Tax/GST, Partners, Content, Automation, Operations, Tasks, Reports, and Settings workspaces incrementally.
- [ ] Add server-enforced founder role, saved layout/filters, command palette, notification inbox, and constrained copilot proposals.
- [ ] Verify mobile action layout and desktop control-room layout with screenshots and live-data provenance.

### Checkpoint 4

- [ ] Every KPI has source, range, freshness, status, calculation, and matching drill-down.
- [ ] No demo metrics appear in production.
- [ ] Role and approval boundaries pass negative tests.

## Phase 5 — Research, Knowledge, and Publishing

- [ ] Add idempotent daily research job with bounded budget, catch-up semantics, source retention, and pause switch.
- [ ] Add ranked backlog and protected-change review gates.
- [ ] Add `/learn` categories, search, metadata, sitemap, structured data, revisions, and rollback.
- [ ] Add reviewed English/Gujarati workflow and social draft queue with disconnected-account honesty.
- [ ] Verify one evergreen article from sourced draft to publish and rollback.

### Checkpoint 5

- [ ] Untrusted web content cannot execute commands or bypass review.
- [ ] Time-sensitive financial content remains pending qualified review.
- [ ] Research and publishing budgets/caps are enforced server-side.

## Phase 6 — SSD Runtime and Hosting Migration

- [ ] Resolve SSD filesystem compatibility without automatic erasure; establish stable volume identity and layout.
- [ ] Move database, documents, backups, uploads, and logs to SSD with fail-closed mount checks.
- [ ] Add tested start/stop/restart/health/backup/restore/update commands.
- [ ] Add bounded launchd jobs for web, scheduler, backup, and health checks with no duplicate legacy jobs.
- [ ] Configure HTTPS exposure using the smallest secure option supported by the actual network.
- [ ] Run production-like auth/payment/backup/restore/offline/SSD-removal tests.
- [ ] Switch `dhansetuhub.in` with rollback; retain old hosting through the rollback window.

### Checkpoint 6 — Acceptance

- [ ] Exactly one canonical repository, database authority, scheduler, startup method, and deployment target are active.
- [ ] Missing SSD prevents startup; reconnecting enables controlled recovery.
- [ ] Real owner-authorized Google sign-in and Razorpay evidence is recorded or explicitly blocked.
- [ ] No old OS service or daily job remains active.
- [ ] Final archive, quarantine, retention, and deletion manifests are exact and secret-free.
