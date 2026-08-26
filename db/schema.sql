-- Shakthi AI OS — Phase 0.1 local schema (SQLite)
-- Dev-mode stand-in for the Postgres + pgvector schema in the v1/v2 architecture doc.
-- Same table shapes, tenant_id on every row so the move to Postgres later is a
-- data migration, not a redesign. SQLite has no row-level security and no
-- pgvector — that's exactly why production moves to Postgres before this
-- carries real multi-business traffic (see README "Known gaps").

CREATE TABLE IF NOT EXISTS businesses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL DEFAULT 'founder',
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agents (
  id TEXT PRIMARY KEY,
  layer TEXT NOT NULL,
  name TEXT NOT NULL,
  default_model_tier TEXT NOT NULL,          -- 'local' | 'cloud'
  local_model TEXT,
  allowed_scope TEXT NOT NULL DEFAULT 'single_business',  -- 'single_business' | 'cross_tenant'
  allowed_tools TEXT NOT NULL DEFAULT '[]',   -- JSON array of tool names. Permission
                                               -- model lives here, not a join table --
                                               -- tools live in a Python dict, not a
                                               -- table, so a join buys no referential
                                               -- integrity, just sync overhead.
  role_prompt TEXT NOT NULL,
  squad TEXT                                  -- founder-assigned team grouping, purely
                                               -- organizational -- does not affect routing.
                                               -- Only present on a fresh DB; the existing
                                               -- live DB gets it via the ALTER TABLE
                                               -- migration in db.init_db() (CREATE TABLE
                                               -- IF NOT EXISTS won't add a column to a
                                               -- table that already exists).
);

CREATE TABLE IF NOT EXISTS sites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  business_id INTEGER NOT NULL REFERENCES businesses(id),
  domain TEXT NOT NULL,
  template_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'planned',     -- planned | generated | deployed | error
  local_path TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL DEFAULT 'founder',
  business_id INTEGER REFERENCES businesses(id),
  agent_id TEXT NOT NULL REFERENCES agents(id),
  goal TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',      -- pending | done | failed
  risk_level TEXT NOT NULL DEFAULT 'normal',   -- normal | critical
  result TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS task_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL REFERENCES tasks(id),
  event_type TEXT NOT NULL,   -- dispatch | validate_fail | escalate | result
  payload TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cost_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL REFERENCES tasks(id),
  agent_id TEXT NOT NULL,
  model TEXT NOT NULL,
  provider TEXT NOT NULL,      -- ollama | claude
  tokens_in INTEGER DEFAULT 0,
  tokens_out INTEGER DEFAULT 0,
  cost_usd REAL DEFAULT 0.0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL DEFAULT 'founder',
  layer TEXT NOT NULL,          -- session | project | business | strategic | lesson
  business_id INTEGER REFERENCES businesses(id),
  content TEXT NOT NULL,
  tags TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Phase 0.2 -------------------------------------------------------------

-- Fine-grained tool-call audit log. Every attempt is logged, including
-- denied ones -- an attempted-but-blocked action is exactly what an audit
-- trail exists to show. business_id sits directly on the row (not just
-- reachable via task_id) following cost_ledger's own precedent, since tool
-- calls are inherently business-scoped and get queried that way.
CREATE TABLE IF NOT EXISTS tool_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL REFERENCES tasks(id),
  agent_id TEXT NOT NULL,
  business_id INTEGER,
  tool_name TEXT NOT NULL,
  params TEXT,
  decision TEXT NOT NULL,       -- allowed | denied | dry_run
  denial_reason TEXT,
  output_summary TEXT,
  duration_ms INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- CEO decision reports. One row per decision, scored on the 3 axes the
-- founder asked for (priority / risk / business impact), not the full
-- 6-score framework from the v1 architecture doc -- that's a later
-- extension if it proves useful, not assumed up front.
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

-- Manually-logged revenue/expense per business. No billing integration
-- exists (nothing to pull real revenue from yet) -- this is the founder's
-- (or Finance agent's, on the founder's instruction) input surface until
-- one does.
CREATE TABLE IF NOT EXISTS finance_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  business_id INTEGER NOT NULL REFERENCES businesses(id),
  type TEXT NOT NULL,            -- revenue | expense
  category TEXT NOT NULL DEFAULT 'general',  -- e.g. general | marketing | hosting | tools | payroll
  amount REAL NOT NULL,
  description TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Security review snapshots. Findings are deterministic checks (secret
-- patterns, permission/audit review, site heuristics) -- not a local
-- model's judgment call -- see orchestrator/security.py.
CREATE TABLE IF NOT EXISTS security_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  business_id INTEGER REFERENCES businesses(id),
  score INTEGER NOT NULL,        -- 0-100
  findings TEXT NOT NULL,        -- JSON array
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Phase 0.4 -------------------------------------------------------------

-- Real error capture from CLI/API top-level exception handlers -- this is
-- what "analyze logs" actually scans, not a simulated log.
CREATE TABLE IF NOT EXISTS error_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,          -- cli | api
  module TEXT,
  message TEXT NOT NULL,
  traceback TEXT,
  bug_id INTEGER,                -- set once triaged into a bug row
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Bug Database. The target is this platform's own codebase, not a
-- business workspace -- see orchestrator/bugfix_tools.py for why that
-- means a completely separate, more restrictive path-containment scheme
-- than the per-business tools.
CREATE TABLE IF NOT EXISTS bugs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  severity TEXT NOT NULL DEFAULT 'P2',       -- P0 Critical | P1 High | P2 Medium | P3 Low | P4 Trivial
                                              -- see orchestrator/bug_fixer.py SEVERITY_LABELS
  status TEXT NOT NULL DEFAULT 'open',       -- open | analyzing | patch_proposed |
                                              -- ceo_approved | ceo_rejected | fix_applied |
                                              -- verified | regressed | closed
  source TEXT NOT NULL DEFAULT 'manual',     -- manual | test_failure | task_failure | error_log
  file_path TEXT,
  function_name TEXT,
  module_name TEXT,
  line_number INTEGER,
  root_cause TEXT,
  fix_recommendation TEXT,
  confidence INTEGER,                        -- 0-100
  related_task_id INTEGER REFERENCES tasks(id),
  related_error_id INTEGER REFERENCES error_log(id),
  patch_path TEXT,                           -- staged patch, never the live file -- see bugfix_tools.py
  current_patch_id INTEGER,                  -- points into patches(id) below
  applied_at TEXT,
  occurrence_count INTEGER NOT NULL DEFAULT 1,  -- bumped when a new scan candidate
                                                 -- matches this bug's (file, function) --
                                                 -- see bug_fixer._check_recurrence()
  duplicate_of INTEGER REFERENCES bugs(id),  -- set when THIS bug is a recurrence of an
                                              -- earlier one; the earlier bug's
                                              -- occurrence_count is what's authoritative
  regression_count INTEGER NOT NULL DEFAULT 0,  -- bumped each time a 'verified' bug
                                                 -- fails tests again
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Fix Tracking / Regression Tracking -- one append-only lifecycle trail
-- per bug, same shape as task_events. Never deleted or overwritten --
-- this table IS the bug's permanent history.
CREATE TABLE IF NOT EXISTS bug_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bug_id INTEGER NOT NULL REFERENCES bugs(id),
  event_type TEXT NOT NULL,   -- detected | analyzed | patch_proposed | qa_reviewed |
                               -- security_reviewed | ceo_approved | ceo_rejected |
                               -- patch_applied | tests_run | verified | regressed | recurred
  payload TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Patch Registry. One row per proposal attempt (a bug can be re-proposed
-- after a QA/Security rejection, and each attempt is kept, not overwritten
-- -- this is the audit trail for "what did the Engineer agent actually
-- write, and when"). full_file_path is the complete corrected file staged
-- for review; diff_path is a human-reviewable unified diff of the same
-- change -- see bug_fixer.propose_patch().
CREATE TABLE IF NOT EXISTS patches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bug_id INTEGER NOT NULL REFERENCES bugs(id),
  target_file TEXT NOT NULL,      -- the real codebase path this would patch
  full_file_path TEXT NOT NULL,   -- staged complete corrected file (never the live file)
  diff_path TEXT,                 -- staged unified diff, for human review
  applied INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Full-codebase audits. One row per audit run; findings are the individual
-- issues it turned up. severity_score is 0-100, 100 = cleanest. See
-- orchestrator/audit.py -- checks are deterministic static analysis
-- (Python's ast module, not regex guessing) plus reuse of security.py's
-- pattern scan, not model judgment for the detection step.
CREATE TABLE IF NOT EXISTS audits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  status TEXT NOT NULL DEFAULT 'running',   -- running | completed | failed
  severity_score INTEGER,
  findings_count INTEGER NOT NULL DEFAULT 0,
  files_affected INTEGER NOT NULL DEFAULT 0,
  executive_summary TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  completed_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_findings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  audit_id INTEGER NOT NULL REFERENCES audits(id),
  category TEXT NOT NULL,     -- bug | duplicate_code | security | performance |
                               -- missing_error_handling | dead_code | unused_file | missing_tests
  severity TEXT NOT NULL,     -- P0-P4
  file_path TEXT,
  line_number INTEGER,
  description TEXT NOT NULL,
  recommendation TEXT,
  bug_id INTEGER REFERENCES bugs(id),   -- set if escalated into the bug pipeline
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Phase v4 (SHAKTHI OS) ------------------------------------------------

-- Sentinel health snapshots. Every field here comes from a real reading
-- (psutil, a live Ollama/DB check) at insert time -- see orchestrator/
-- sentinel.py. NULL means "not available on this machine" (e.g. CPU temp
-- needs sudo), never a placeholder value.
CREATE TABLE IF NOT EXISTS system_health (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cpu_percent REAL,
  cpu_freq_mhz REAL,
  cpu_temp_c REAL,             -- NULL on this machine -- powermetrics needs sudo
  ram_percent REAL,
  swap_percent REAL,
  disk_percent REAL,
  battery_percent REAL,
  battery_plugged INTEGER,
  internet_ok INTEGER,
  ollama_ok INTEGER,
  db_ok INTEGER,
  active_tasks INTEGER,
  untriaged_errors INTEGER,
  health_score INTEGER,        -- 0-100
  performance_score INTEGER,   -- 0-100
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge base. Plain-text search (no embeddings yet -- same recency/
-- keyword-only stance as memory_entries in Phase 0.1, same upgrade path
-- noted there: nomic-embed-text via Ollama, later).
CREATE TABLE IF NOT EXISTS knowledge_documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category TEXT NOT NULL DEFAULT 'general',   -- sop | note | reference | general
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  tags TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Buddy conversation log -- kept short-lived context per session_id, and
-- a permanent audit trail of anything Safe Mode blocked (see buddy.py).
CREATE TABLE IF NOT EXISTS buddy_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  mode TEXT NOT NULL,          -- child | family | general
  message TEXT NOT NULL,
  response TEXT,
  blocked_reason TEXT,         -- set if Safe Mode blocked this message
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Voice command log -- every transcription + routing decision, so a
-- misheard command is debuggable after the fact.
CREATE TABLE IF NOT EXISTS voice_commands (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  identity TEXT NOT NULL,       -- owner | family | guest
  raw_transcript TEXT NOT NULL,
  detected_language TEXT,
  language_confidence REAL,
  routed_agent TEXT,
  routed_action TEXT,
  denied_reason TEXT,           -- set if identity lacked permission for the routed action
  result_summary TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Website Builder pipeline. Additive to sites (which still tracks the
-- actual generated file) -- this tracks the governance workflow around
-- ONE project's file: Founder Request -> CEO -> Requirements -> Build ->
-- QA -> Security -> Package. sitegen.py / the existing sites table are
-- untouched; this is a parallel, richer pipeline for the 7 new site
-- types, not a replacement for the Phase 0.2 single-template foundation.
CREATE TABLE IF NOT EXISTS website_projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  business_id INTEGER REFERENCES businesses(id),
  site_type TEXT NOT NULL,        -- landing_page | business_site | blog | saas_ui |
                                   -- admin_dashboard | crm_frontend | internal_tool
  founder_request TEXT NOT NULL,
  requirements TEXT,              -- JSON, from the requirements-generation step
  status TEXT NOT NULL DEFAULT 'requested',
    -- requested | ceo_approved | ceo_rejected | requirements_ready | built |
    -- qa_passed | qa_failed | security_passed | security_failed | packaged | failed
  ceo_decision_id INTEGER REFERENCES decisions(id),
  qa_notes TEXT,
  security_score INTEGER,
  security_findings TEXT,         -- JSON
  site_id INTEGER REFERENCES sites(id),
  deployment_package_path TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- SHAKTHI Correction Bot -- "Senior Reviewer / Final Quality Controller".
-- Runs Task Complete -> Correction Review -> QA Review -> Security Review
-- -> Final Approval on the output of another already-completed task (a
-- patch, a generated site, an audit summary, ...). correction_score is how
-- clean the ORIGINAL content was (100 = no issues found); quality_score is
-- the FINAL (post-correction) content's quality. See orchestrator/
-- correction_bot.py.
CREATE TABLE IF NOT EXISTS corrections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_type TEXT NOT NULL,        -- code | writing | business_report | website_content | seo_content
  task_ref TEXT,                  -- free-text pointer to the source, e.g. "bug_fixer:patch:12"
  business_id INTEGER REFERENCES businesses(id),
  status TEXT NOT NULL DEFAULT 'running',   -- running | completed | failed
  correction_score INTEGER,
  quality_score INTEGER,
  issues_found INTEGER NOT NULL DEFAULT 0,
  issues_fixed INTEGER NOT NULL DEFAULT 0,
  qa_status TEXT,                 -- pass | fail
  security_status TEXT,           -- pass | fail
  final_status TEXT,              -- approved | revise
  original_content TEXT,
  corrected_content TEXT,
  summary TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  completed_at TEXT
);

CREATE TABLE IF NOT EXISTS correction_findings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  correction_id INTEGER NOT NULL REFERENCES corrections(id),
  category TEXT NOT NULL,     -- placeholder_text | grammar | code_quality | secret | dangerous_pattern | seo | accessibility | inconsistency
  description TEXT NOT NULL,
  auto_fixed INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Operation First Revenue -- Offer A payment collection. Razorpay Payment
-- Links only (no webhook receiver -- this system is localhost-only by
-- design, see README "Security gaps"; status is checked on demand via the
-- Payment Links fetch API, not pushed to us). Key ID / Key Secret are
-- NEVER stored -- same manual-entry-every-invocation rule as Telegram and
-- Google Sheets credentials. See orchestrator/payments.py.
CREATE TABLE IF NOT EXISTS payment_links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  razorpay_link_id TEXT NOT NULL UNIQUE,
  short_url TEXT NOT NULL,
  amount_inr REAL NOT NULL,
  description TEXT NOT NULL,
  customer_name TEXT,
  customer_contact TEXT,
  reference_id TEXT,          -- e.g. "web-audit:dhansetuhub.in"
  status TEXT NOT NULL DEFAULT 'created',   -- created | partially_paid | paid | cancelled | expired
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  last_checked_at TEXT
);

-- SHAKTHI Chrome Developer Bot -- website review pipeline (real
-- browser-driven checks via Playwright, not just urllib). seo_score and
-- conversion_score are new metrics distinct from WEB-001's Website
-- Health/Security/Performance scores -- see orchestrator/chrome_developer.py.
CREATE TABLE IF NOT EXISTS website_reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  business_id INTEGER REFERENCES businesses(id),
  status TEXT NOT NULL DEFAULT 'running',   -- running | completed | failed
  seo_score INTEGER,
  conversion_score INTEGER,
  ui_score INTEGER,
  deployment_ready INTEGER,                 -- 0/1 -- set by the CEO gate, see chrome_developer.review_website()
  findings_count INTEGER NOT NULL DEFAULT 0,
  summary TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  completed_at TEXT
);

CREATE TABLE IF NOT EXISTS website_review_findings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  review_id INTEGER NOT NULL REFERENCES website_reviews(id),
  category TEXT NOT NULL,    -- seo | conversion | performance | console_error | security | mobile
  severity TEXT NOT NULL,    -- P0-P4
  description TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- payment_gateway_manager.py's generic ledger for Stripe/Subscriptions/UPI
-- -- Razorpay Payment Links keep using the existing payment_links table
-- (payments.py) untouched; this covers the 3 new methods this table
-- didn't originally shape for.
CREATE TABLE IF NOT EXISTS payment_transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  gateway TEXT NOT NULL,       -- razorpay_subscription | stripe_checkout | upi
  gateway_ref TEXT,            -- the gateway's own id -- NULL for UPI (no account/API involved)
  amount REAL,
  currency TEXT NOT NULL DEFAULT 'INR',
  description TEXT NOT NULL,
  customer_name TEXT,
  customer_contact TEXT,
  status TEXT NOT NULL DEFAULT 'created',   -- created | paid | failed | cancelled
  business_id INTEGER REFERENCES businesses(id),
  url_or_link TEXT,             -- checkout URL / UPI deep link
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- SHAKTHI Worker Pool -- execution/concurrency layer, NOT a decision-
-- maker. Workers never call ceo.decide() themselves and never approve/
-- reject anything; they just run an existing module's already-built
-- function (chrome_developer.review_website, security.security_posture_
-- scan, sentinel.collect_health, ...) and report the result back. See
-- orchestrator/worker_pool.py, load_manager.py, worker_registry.py.
CREATE TABLE IF NOT EXISTS workers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  worker_type TEXT NOT NULL,      -- rapid | engineering | infra
  status TEXT NOT NULL DEFAULT 'idle',   -- idle | busy | failed
  concurrency_limit INTEGER NOT NULL,
  tasks_completed INTEGER NOT NULL DEFAULT 0,
  tasks_failed INTEGER NOT NULL DEFAULT 0,
  last_active_at TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS work_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,             -- see worker_registry.TASK_KINDS
  payload TEXT NOT NULL DEFAULT '{}',   -- JSON kwargs for the target function
  priority INTEGER NOT NULL DEFAULT 5,  -- lower = higher priority
  status TEXT NOT NULL DEFAULT 'queued',  -- queued | running | done | failed
  assigned_worker_type TEXT,
  assigned_worker_id INTEGER REFERENCES workers(id),
  result TEXT,                    -- JSON, set on success
  error TEXT,                     -- set on failure
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  started_at TEXT,
  completed_at TEXT
);

-- Emergency Response Team (ERT) -- incident tracking. incident_number is
-- the human-facing "INC-2026-001" id; `id` is the normal autoincrement PK
-- everything else in this schema uses. See orchestrator/incident_manager.py,
-- incident_registry.py (ownership matrix), incident_scheduler.py
-- (automatic detection), incident_audit.py (postmortems).
CREATE TABLE IF NOT EXISTS incidents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_number TEXT NOT NULL UNIQUE,   -- INC-2026-001
  incident_type TEXT NOT NULL,            -- see incident_registry.OWNERSHIP_MATRIX keys
  severity TEXT NOT NULL,                 -- P0 | P1 | P2 | P3
  owner TEXT NOT NULL,
  support_team TEXT NOT NULL DEFAULT '[]',  -- JSON list
  status TEXT NOT NULL DEFAULT 'NEW',
    -- NEW | ACKNOWLEDGED | INVESTIGATING | FIXING | VERIFYING |
    -- READY_TO_DEPLOY | RESOLVED | CLOSED
  description TEXT NOT NULL,
  root_cause TEXT,
  fix_applied TEXT,
  detected_by TEXT NOT NULL DEFAULT 'manual',  -- 'manual' | 'incident_scheduler'
  recovery_action TEXT,
  recovery_result TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  acknowledged_at TEXT,
  resolved_at TEXT,
  closed_at TEXT
);

CREATE TABLE IF NOT EXISTS incident_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_id INTEGER NOT NULL REFERENCES incidents(id),
  event_type TEXT NOT NULL,   -- state_change | note | recovery_attempt | notification
  detail TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Pricing/usage gating -- pricing.py. product is 'pdf_studio' | 'peopledesk'
-- (peopledesk has no product to attach to yet; the pricing config exists
-- so it's ready the moment it does). email is the only identity concept
-- this project has for paying customers -- no login system, no accounts.
CREATE TABLE IF NOT EXISTS product_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  product TEXT NOT NULL,
  use_count INTEGER NOT NULL DEFAULT 0,
  first_used_at TEXT DEFAULT CURRENT_TIMESTAMP,
  last_used_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(email, product)
);

CREATE TABLE IF NOT EXISTS product_subscriptions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  product TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',   -- pending | active | expired | cancelled
  valid_until TEXT,
  amount_inr REAL NOT NULL,
  gateway TEXT NOT NULL,          -- razorpay | payu
  gateway_ref TEXT,               -- payment link id / PayU txnid
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Sales agent activation. A lead is the real trigger every sales.py
-- function hangs off of -- ingest_lead() is the "new lead / inbound / CRM
-- event" entry point the founder's spec asked for. owner flips from
-- 'sales' to 'founder' the moment negotiation intent crosses the
-- escalation threshold (see sales.py:flag_for_founder).
CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  business_id INTEGER REFERENCES businesses(id),
  name TEXT,
  email TEXT,
  contact TEXT,
  source TEXT NOT NULL,             -- website_form | referral | cold_list | inbound_email | marketing | ...
  status TEXT NOT NULL DEFAULT 'new',   -- new | scored | contacted | negotiating | won | lost
  score REAL,                       -- fit/urgency, 0.00-1.00, from sales.score_lead()
  score_reason TEXT,
  last_contact_at TEXT,
  next_action TEXT,
  owner TEXT NOT NULL DEFAULT 'sales',  -- 'sales' | 'founder'
  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Audit trail per lead, same task_events pattern as everything else in
-- this project -- and task_id ties each event back to the real sales-agent
-- `tasks` row that produced it, so "0 tasks ever routed to sales" is
-- falsifiable by construction going forward, not just claimed fixed.
CREATE TABLE IF NOT EXISTS lead_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id INTEGER NOT NULL REFERENCES leads(id),
  event_type TEXT NOT NULL,   -- scored | outreach_drafted | proposal_drafted | escalated | status_change
  payload TEXT,
  task_id INTEGER REFERENCES tasks(id),
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Marketing agent's output queue -- top-of-funnel drafts (LinkedIn posts,
-- landing copy variants, cold email sequences, ad angles). marketing.py
-- writes here; marketing.send_to_sales() is the wired hand-off that moves
-- a variant from here into a real sales.py task.
CREATE TABLE IF NOT EXISTS content_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  business_id INTEGER REFERENCES businesses(id),
  content_type TEXT NOT NULL,   -- linkedin_post | twitter_thread | landing_copy | cold_email | ad_angle |
                                 -- reel_script | visual_prompt | instagram_post (Dhansetu AI additions)
  variant_label TEXT,           -- 'A' / 'B' / 'C' for A/B/C variants of the same brief
  target TEXT,                  -- what this was written for, e.g. 'core_offer'
  content TEXT NOT NULL,
  icp_fit_score REAL,
  status TEXT NOT NULL DEFAULT 'draft',   -- draft | sent_to_sales | ready_to_post | used | archived
  platform TEXT,                -- 'instagram' | NULL -- only Dhansetu AI sets this; marketing.py
                                 -- never touches it, existing rows/behavior unaffected
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Daily team work register -- a real human team of expert engineers/staff
-- (not AI agents, not the AI Worker Pool's thread pools in the `workers`
-- table above -- same word, unrelated concept), not wage laborers -- that
-- was the founder's own example, not the real composition of the team.
-- One row per team member per day, same as a daily standup/work log. No
-- pay tracking -- explicitly out of scope per the founder's own answer
-- (work assigned/done, attendance, hours only).
CREATE TABLE IF NOT EXISTS team_members (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  business_id INTEGER REFERENCES businesses(id),
  name TEXT NOT NULL,
  role TEXT,                     -- free text, e.g. 'backend engineer', 'ML engineer', 'DevOps'
  contact TEXT,
  status TEXT NOT NULL DEFAULT 'active',   -- active | inactive
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_work_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  worker_id INTEGER NOT NULL REFERENCES team_members(id),
  business_id INTEGER REFERENCES businesses(id),
  work_date TEXT NOT NULL,       -- 'YYYY-MM-DD'
  present INTEGER NOT NULL DEFAULT 1,   -- 0/1 -- SQLite has no native boolean
  hours_worked REAL,
  work_assigned TEXT,
  work_done TEXT,
  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(worker_id, work_date)   -- one real entry per worker per day, enforced -- not just a convention
);

-- Agent skill test / 100-point review -- orchestrator/skill_test.py. Each
-- agent gets one real test task grounded in its own role_prompt, run
-- through the real routing.run_task() pipeline (a real `tasks` row, not a
-- side-channel call), then graded on 3 dimensions (25 pts each) by a
-- separate reviewer call, plus a 4th dimension (25 pts) from real
-- production task history when the agent has any. Honest limitation
-- stated in code, not hidden: the reviewer is the same tier of local
-- model being tested (no cloud key is set this session by design), so
-- this is a real but limited signal, not an authoritative assessment.
CREATE TABLE IF NOT EXISTS skill_reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id TEXT NOT NULL REFERENCES agents(id),
  test_goal TEXT NOT NULL,
  response TEXT NOT NULL,
  relevance_score INTEGER,
  guardrails_score INTEGER,
  clarity_score INTEGER,
  history_score INTEGER,
  has_history INTEGER NOT NULL DEFAULT 0,
  total_score INTEGER NOT NULL,
  deterministic_check TEXT,      -- JSON: {"name": ..., "passed": bool} for the handful of
                                  -- agents with an objectively-checkable right answer
  possible_fabrication INTEGER NOT NULL DEFAULT 0,   -- regex cross-check: a ₹/$ figure in the
                                                      -- response that wasn't in the test prompt
  notes TEXT,
  task_id INTEGER REFERENCES tasks(id),
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Dhansetu AI -- a deliberately separate course-selling branch, its own
-- squad, its own agents, own tables -- does not touch marketing.py/sales.py
-- or their data at all. content_queue.platform (added via migration below,
-- same reason as agents.squad) is the one shared, purely-additive column;
-- everything else here is new.
CREATE TABLE IF NOT EXISTS courses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  business_id INTEGER REFERENCES businesses(id),
  title TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'gu',    -- Gujarati by default, per the brief
  outline TEXT,
  sales_copy TEXT,
  source TEXT,                            -- 'google_sheet:<spreadsheet_id>' | 'manual'
  status TEXT NOT NULL DEFAULT 'drafted',   -- drafted | ready | published
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- The Dhansetu AI Instagram bio-link page ("link tree"). Founder adds real
-- entries via CLI; starts empty on purpose -- no placeholder/fake links
-- ship by default, the public page below states plainly when it's empty.
CREATE TABLE IF NOT EXISTS link_tree_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  business_id INTEGER REFERENCES businesses(id),
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- blackboxOps_OS AI Employee Onboarding -- Stage 1 (Business Discovery)
-- ONLY. Stages 2-9 of the founder's spec (generating 12 AI employee
-- types, KPI dashboards, Microsoft-tools automation, knowledge base,
-- reporting) are explicitly out of scope until Stage 1 is real and
-- reviewed -- not built silently ahead of that.
CREATE TABLE IF NOT EXISTS business_discoveries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  business_name TEXT NOT NULL,
  industry TEXT,
  website TEXT,
  business_model TEXT,
  target_customer TEXT,
  revenue_streams TEXT,
  team_size TEXT,
  monthly_revenue_range TEXT,
  main_challenges TEXT,
  preferred_tools TEXT,
  current_software TEXT,
  growth_goal_12mo TEXT,
  revenue_bottlenecks TEXT,
  operational_bottlenecks TEXT,
  marketing_bottlenecks TEXT,
  sales_bottlenecks TEXT,
  support_bottlenecks TEXT,
  status TEXT NOT NULL DEFAULT 'intake',   -- intake | analyzed
  task_id INTEGER REFERENCES tasks(id),
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Founder-facing high-level work tracker: "Task 1", "Task 2", ... --
-- distinct from the low-level `tasks` table (one row per agent call).
-- An initiative is a standing piece of real work the founder asked for
-- (e.g. "the Rs.1 Cr plan"), shown on the dashboard with a real percent-
-- complete computed from its own milestones -- never a hand-picked
-- number. Multiple initiatives can be 'running' at once by design (the
-- founder explicitly asked for prior tasks to keep running alongside
-- new ones, not get replaced by them).
CREATE TABLE IF NOT EXISTS initiatives (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seq INTEGER NOT NULL UNIQUE,             -- Task 1, Task 2, ... shown to the founder
  title TEXT NOT NULL,
  artifact_url TEXT,                       -- linked artifact/plan page, if any
  status TEXT NOT NULL DEFAULT 'running',  -- running | paused | done
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS initiative_milestones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  initiative_id INTEGER NOT NULL REFERENCES initiatives(id),
  title TEXT NOT NULL,
  done INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  done_at TEXT
);

-- Failure Analysis Engine (Task 4, scoped down from the founder's full
-- "ANGELLA OMEGA" Six Sigma/DMAIC spec per a real CEO decision -- see
-- decisions#11: build one high-leverage process, root-cause analysis for
-- a real recurring failure, not the whole framework at once). A real 5-
-- Whys record per genuine failure, not a hypothetical template.
CREATE TABLE IF NOT EXISTS failure_analyses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_type TEXT NOT NULL,               -- bug | task_failure | incident | manual
  source_id INTEGER,                       -- id in the relevant table, if applicable
  title TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'P2',     -- same P0-P4 scale as bugs.severity
  summary TEXT NOT NULL,
  five_whys TEXT NOT NULL,                 -- JSON array of strings, why #1 -> #5
  root_cause TEXT NOT NULL,
  corrective_action TEXT NOT NULL,         -- what was actually done about it
  preventive_action TEXT NOT NULL,         -- the poka-yoke: what stops this recurring
  lessons_learned TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',     -- open | closed (corrective+preventive both applied)
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Dhansetu PeopleDesk (Task 5) -- a real staff/attendance/payroll tool for
-- local small businesses and small industrial units. Same no-real-auth,
-- email-is-identity model as PDF Studio (product_subscriptions/
-- product_usage) -- whoever's browser has that email owns that email's
-- staff list. Deliberately lean MVP: a directory, daily attendance, and a
-- deterministic payroll summary computed from real attendance x wage --
-- not a full HRMS (leave policies, tax, payslips) on day one.
CREATE TABLE IF NOT EXISTS peopledesk_staff (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_email TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT,
  phone TEXT,
  pay_type TEXT NOT NULL DEFAULT 'daily',   -- daily | monthly
  daily_wage_inr REAL,                      -- set when pay_type = 'daily'
  monthly_salary_inr REAL,                  -- set when pay_type = 'monthly'
  join_date TEXT,
  status TEXT NOT NULL DEFAULT 'active',    -- active | inactive
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS peopledesk_attendance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  staff_id INTEGER NOT NULL REFERENCES peopledesk_staff(id),
  attendance_date TEXT NOT NULL,            -- YYYY-MM-DD
  status TEXT NOT NULL,                     -- present | absent | half_day | leave
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(staff_id, attendance_date)
);

-- Trading OS (Task 6) -- Phase 1 per a real CEO decision (decisions#12):
-- crypto spot ONLY, paper trading ONLY (simulated fills against real
-- market prices, never a real broker order), one asset class before
-- expanding. Nifty options and real broker execution are explicit later
-- phases, not built here. Every simulated trade is auto-journaled --
-- the founder's own explicit requirement.
CREATE TABLE IF NOT EXISTS trading_strategies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  symbol TEXT NOT NULL,                    -- e.g. 'BTCUSDT' -- a real Binance pair
  rule_type TEXT NOT NULL,                 -- sma_crossover | rsi_threshold
  params TEXT NOT NULL,                    -- JSON, shape depends on rule_type
  status TEXT NOT NULL DEFAULT 'active',   -- active | paused
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS paper_positions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  strategy_id INTEGER NOT NULL REFERENCES trading_strategies(id),
  symbol TEXT NOT NULL,
  quantity REAL NOT NULL,
  entry_price REAL NOT NULL,
  exit_price REAL,
  status TEXT NOT NULL DEFAULT 'open',     -- open | closed
  opened_at TEXT DEFAULT CURRENT_TIMESTAMP,
  closed_at TEXT
);

-- Trading journal -- append-only, every simulated fill (entry and exit),
-- never edited or deleted. pnl is in the pair's real quote currency
-- (USDT for a *USDT pair) -- never mislabeled as INR, that would be a
-- real correctness bug, not a display choice.
CREATE TABLE IF NOT EXISTS trading_journal (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  position_id INTEGER NOT NULL REFERENCES paper_positions(id),
  strategy_id INTEGER NOT NULL REFERENCES trading_strategies(id),
  symbol TEXT NOT NULL,
  action TEXT NOT NULL,                    -- entry | exit
  quantity REAL NOT NULL,
  price REAL NOT NULL,
  pnl REAL,                                -- set only on exit, in quote currency
  reason TEXT NOT NULL,                    -- what triggered this, e.g. "SMA10 crossed above SMA30"
  executed_at TEXT DEFAULT CURRENT_TIMESTAMP
);
