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
  role_prompt TEXT NOT NULL
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
