-- DhanSetu product foundation. Forward-only production migration.
-- Rollback: disable new routes, export affected rows, then use a reviewed
-- follow-up migration; do not drop customer data automatically.
begin;

create table if not exists public.budget_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  monthly_income_paise bigint not null default 0 check (monthly_income_paise >= 0),
  cadence text not null default 'monthly' check (cadence in ('monthly','fortnightly','weekly','irregular')),
  household_size integer not null default 1 check (household_size > 0),
  fixed_obligations_paise bigint not null default 0 check (fixed_obligations_paise >= 0),
  variable_budget_paise bigint not null default 0 check (variable_budget_paise >= 0),
  savings_target_paise bigint not null default 0 check (savings_target_paise >= 0),
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);

create table if not exists public.money_transactions (
  id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade,
  occurred_on date not null, description text not null, merchant text, category text not null default 'uncategorised',
  amount_paise bigint not null check (amount_paise <> 0), direction text not null check (direction in ('income','expense')),
  source text not null default 'manual' check (source in ('manual','csv','sms')), source_ref text,
  import_fingerprint text, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique(user_id, import_fingerprint)
);
create index if not exists money_transactions_user_date_idx on public.money_transactions(user_id, occurred_on desc);

create table if not exists public.tax_estimates (
  id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade,
  assessment_year text not null, regime text not null check (regime in ('old','new')), input_json jsonb not null,
  result_json jsonb not null, rule_version text not null, evidence_status text not null default 'self_reported' check (evidence_status in ('self_reported','partially_verified','verified_by_user')),
  created_at timestamptz not null default now()
);
create index if not exists tax_estimates_user_created_idx on public.tax_estimates(user_id, created_at desc);

create table if not exists public.gst_reconciliations (
  id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade,
  period text not null, source text not null check (source in ('purchase_register','gstr_2b','bank')), input_hash text not null,
  result_json jsonb not null, review_status text not null default 'needs_review' check (review_status in ('needs_review','reviewed','approved_by_user')),
  created_at timestamptz not null default now()
);

create table if not exists public.partner_applications (
  id uuid primary key default gen_random_uuid(), applicant_user_id uuid references auth.users(id) on delete set null,
  kind text not null check (kind in ('affiliate','tax_provider','gst_provider','career_provider','insurance_partner')),
  display_name text not null, contact_email text not null, notes text, status text not null default 'pending_review' check (status in ('pending_review','approved','rejected','suspended')),
  disclosure_accepted_at timestamptz, created_at timestamptz not null default now()
);

create table if not exists public.referral_links (
  id uuid primary key default gen_random_uuid(), partner_id uuid not null references public.partner_applications(id) on delete cascade,
  code text not null unique, destination text not null default '/', created_at timestamptz not null default now()
);

create table if not exists public.commission_events (
  id uuid primary key default gen_random_uuid(), partner_id uuid not null references public.partner_applications(id) on delete restrict,
  purchase_id uuid references public.purchases(id) on delete set null, event_type text not null check (event_type in ('eligible','hold','approved','paid','reversed','disputed')),
  amount_paise bigint not null default 0 check (amount_paise >= 0), rate_basis text, source_event_id text not null unique, available_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.founder_expenses (
  id uuid primary key default gen_random_uuid(), expense_date date not null, vendor text not null, category text not null,
  amount_paise bigint not null check (amount_paise >= 0), status text not null default 'entered' check (status in ('entered','verified','void')),
  source_ref text, created_at timestamptz not null default now()
);

create table if not exists public.daily_research_runs (
  id uuid primary key default gen_random_uuid(), run_key text not null unique, started_at timestamptz not null default now(), finished_at timestamptz,
  status text not null default 'running' check (status in ('running','succeeded','failed','skipped')), findings_count integer not null default 0, error_code text
);
create table if not exists public.research_findings (
  id uuid primary key default gen_random_uuid(), fingerprint text not null unique, source_url text not null, source_published_at timestamptz,
  title text not null, summary text not null, confidence text not null check (confidence in ('low','medium','high')), affected_area text not null,
  effective_date date, reviewed_at timestamptz, decision text check (decision in ('pending','accepted','rejected','stale')), created_at timestamptz not null default now()
);
create table if not exists public.improvement_proposals (
  id uuid primary key default gen_random_uuid(), finding_id uuid references public.research_findings(id) on delete set null, title text not null,
  risk_level text not null check (risk_level in ('low','medium','high','protected')), status text not null default 'pending_review' check (status in ('pending_review','approved','implemented','rejected','rolled_back')),
  branch_name text, evidence_json jsonb, created_at timestamptz not null default now()
);

alter table public.budget_profiles enable row level security;
alter table public.money_transactions enable row level security;
alter table public.tax_estimates enable row level security;
alter table public.gst_reconciliations enable row level security;
alter table public.partner_applications enable row level security;
alter table public.referral_links enable row level security;
alter table public.commission_events enable row level security;
alter table public.founder_expenses enable row level security;
alter table public.daily_research_runs enable row level security;
alter table public.research_findings enable row level security;
alter table public.improvement_proposals enable row level security;

drop policy if exists budget_owner on public.budget_profiles;
create policy budget_owner on public.budget_profiles for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists transactions_owner on public.money_transactions;
create policy transactions_owner on public.money_transactions for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists tax_owner on public.tax_estimates;
create policy tax_owner on public.tax_estimates for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists gst_owner on public.gst_reconciliations;
create policy gst_owner on public.gst_reconciliations for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists partner_self on public.partner_applications;
create policy partner_self on public.partner_applications for insert to authenticated with check (auth.uid() = applicant_user_id);
create policy partner_read_self on public.partner_applications for select to authenticated using (auth.uid() = applicant_user_id);
drop policy if exists referral_self on public.referral_links;
create policy referral_self on public.referral_links for select to authenticated using (exists (select 1 from public.partner_applications p where p.id = partner_id and p.applicant_user_id = auth.uid()));
drop policy if exists commission_no_client_read on public.commission_events;
create policy commission_no_client_read on public.commission_events for select to authenticated using (false);
drop policy if exists founder_expenses_no_client_read on public.founder_expenses;
create policy founder_expenses_no_client_read on public.founder_expenses for select to authenticated using (false);
drop policy if exists research_no_client_write on public.daily_research_runs;
create policy research_no_client_write on public.daily_research_runs for select to authenticated using (false);
drop policy if exists findings_no_client_write on public.research_findings;
create policy findings_no_client_write on public.research_findings for select to authenticated using (false);
drop policy if exists proposals_no_client_write on public.improvement_proposals;
create policy proposals_no_client_write on public.improvement_proposals for select to authenticated using (false);

commit;
