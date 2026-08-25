const API_BASE = process.env.API_BASE || process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8787";

export class ApiError extends Error {}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(`API ${path} returned ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export type Business = { id: number; tenant_id: string; name: string };

export type Task = {
  id: number;
  agent_id: string;
  business_id: number | null;
  status: string;
  risk_level: string;
  created_at: string;
};

export type Agent = {
  id: string;
  layer: string;
  name: string;
  default_model_tier: string;
  local_model: string | null;
  allowed_scope: string;
  allowed_tools: string[];
  role_prompt: string;
  squad: string | null;
};

export type Decision = {
  id: number;
  task_id: number | null;
  business_id: number | null;
  goal: string;
  status: string;
  priority_score: number | null;
  risk_score: number | null;
  business_impact_score: number | null;
  reason: string;
  created_at: string;
};

export type CostRow = { provider: string; calls: number; tokens_in: number; tokens_out: number; cost_usd: number };

export type FinanceReport = {
  period: string;
  since: string;
  business_id: number | null;
  api_cost_usd: number;
  ollama_calls: number;
  ollama_estimated_savings_usd: number;
  revenue_usd: number;
  expense_usd: number;
  profit_usd: number;
  cost_by_provider: CostRow[];
};

export type Finding = { type: string; check: string; file?: string; agent?: string; tool?: string };
export type SecurityReport = { id: number; business_id: number | null; score: number; findings: Finding[]; created_at: string };

export type ToolCall = {
  id: number;
  task_id: number;
  agent_id: string;
  business_id: number | null;
  tool_name: string;
  params: string;
  decision: string;
  denial_reason: string | null;
  output_summary: string | null;
  duration_ms: number | null;
  created_at: string;
};

export const getOverview = () =>
  apiGet<{ businesses: Business[]; active_tasks: number; recent_tasks: Task[]; agent_count: number; cost_summary: CostRow[] }>(
    "/api/overview"
  );

export const getAgents = () => apiGet<{ agents: Agent[] }>("/api/agents");

export type Course = {
  id: number;
  business_id: number | null;
  title: string;
  language: string;
  outline: string | null;
  sales_copy: string | null;
  source: string | null;
  status: string;
  created_at: string;
};
export const getDhansetuCourses = (status?: string) =>
  apiGet<{ courses: Course[] }>(`/api/dhansetu/courses${status ? `?status=${status}` : ""}`);

export type DhansetuContentItem = {
  id: number;
  business_id: number | null;
  content_type: string;
  variant_label: string | null;
  target: string | null;
  content: string;
  icp_fit_score: number | null;
  status: string;
  platform: string | null;
  created_at: string;
};
export const getDhansetuContentQueue = () => apiGet<{ items: DhansetuContentItem[] }>("/api/dhansetu/content-queue");

export type LinkTreeEntry = {
  id: number;
  business_id: number | null;
  title: string;
  url: string;
  sort_order: number;
  active: number;
  created_at: string;
};
export const getDhansetuLinks = () => apiGet<{ links: LinkTreeEntry[] }>("/api/dhansetu/links");

export type InitiativeMilestone = {
  id: number;
  initiative_id: number;
  title: string;
  done: number;
  created_at: string;
  done_at: string | null;
};
export type Initiative = {
  id: number;
  seq: number;
  title: string;
  artifact_url: string | null;
  status: "running" | "paused" | "done";
  created_at: string;
  updated_at: string;
  milestones: InitiativeMilestone[];
  milestone_total: number;
  milestone_done: number;
  percent_complete: number;
};
export const getInitiatives = (status?: string) =>
  apiGet<{ initiatives: Initiative[] }>(`/api/initiatives${status ? `?status=${status}` : ""}`);

export type PaAngellaStatus = {
  last_task: { id: number; status: string; created_at: string } | null;
  active: boolean;
  recent_task_count: number;
};
export const getPaAngellaStatus = () => apiGet<PaAngellaStatus>("/api/pa-angella/status");

export type FailureAnalysis = {
  id: number;
  source_type: string;
  source_id: number | null;
  title: string;
  severity: string;
  summary: string;
  five_whys: string[];
  root_cause: string;
  corrective_action: string;
  preventive_action: string;
  lessons_learned: string;
  status: "open" | "closed";
  created_at: string;
};
export const getFailureAnalyses = (status?: string) =>
  apiGet<{ analyses: FailureAnalysis[] }>(`/api/failure-analyses${status ? `?status=${status}` : ""}`);

export type PeopledeskStaff = {
  id: number;
  owner_email: string;
  name: string;
  role: string | null;
  phone: string | null;
  pay_type: "daily" | "monthly";
  daily_wage_inr: number | null;
  monthly_salary_inr: number | null;
  join_date: string | null;
  status: string;
  created_at: string;
};
export const getPeopledeskStaff = (ownerEmail: string) =>
  apiGet<{ staff: PeopledeskStaff[] }>(`/api/peopledesk/staff?owner_email=${encodeURIComponent(ownerEmail)}`);

export type PeopledeskPayrollRow = {
  staff_id: number;
  name: string;
  pay_type: "daily" | "monthly";
  present_days: number;
  half_days: number;
  absent_days: number;
  leave_days: number;
  payable_days: number | null;
  amount_inr: number;
};
export const getPeopledeskPayroll = (ownerEmail: string, dateFrom: string, dateTo: string) =>
  apiGet<{ summary: PeopledeskPayrollRow[] }>(
    `/api/peopledesk/payroll?owner_email=${encodeURIComponent(ownerEmail)}&date_from=${dateFrom}&date_to=${dateTo}`
  );

export const getDecisions = (limit = 20) => apiGet<{ decisions: Decision[] }>(`/api/ceo/decisions?limit=${limit}`);

export type CeoHealth = {
  status: "healthy" | "degraded" | "down" | "unknown";
  failure_count: number;
  degraded_count: number;
  last_error: { task_id: number; goal: string; result: string; at: string } | null;
  recovery_attempts: number;
  total_tracked: number;
};

export const getCeoHealth = () => apiGet<CeoHealth>("/api/ceo/health");

export type GovernorStatus = {
  status: "operational" | "degraded";
  subsystems: Record<string, { ok: boolean; detail: string }>;
  ceo: CeoHealth;
  failover_events_24h: { task_id: number; status: string; goal: string; at: string }[];
  failover_event_count_24h: number;
};

export const getGovernorStatus = () => apiGet<GovernorStatus>("/api/governor");

export type Incident = {
  id: number;
  incident_number: string;
  incident_type: string;
  severity: string;
  owner: string;
  support_team: string[];
  status: string;
  description: string;
  root_cause: string | null;
  fix_applied: string | null;
  detected_by: string;
  recovery_action: string | null;
  recovery_result: string | null;
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
};

export type IncidentEvent = { id: number; incident_id: number; event_type: string; detail: string; created_at: string };

export const getIncidents = (status?: string, severity?: string, limit = 100) => {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (severity) params.set("severity", severity);
  params.set("limit", String(limit));
  return apiGet<{ incidents: Incident[]; mttr_seconds: number | null; open_count: number; critical_count: number }>(`/api/incidents?${params}`);
};

export const getIncidentDetail = (incidentNumber: string) =>
  apiGet<{ incident: Incident; events: IncidentEvent[] }>(`/api/incidents/detail?incident_number=${incidentNumber}`);

export type Worker = {
  id: number;
  name: string;
  worker_type: string;
  status: string;
  concurrency_limit: number;
  tasks_completed: number;
  tasks_failed: number;
  last_active_at: string | null;
};

export type LoadBalancerStatus = {
  queue_depth: number;
  scale_threshold: number;
  max_queue_size: number;
  scaled_up: boolean;
  overflowing: boolean;
  concurrency: Record<string, number>;
};

export type QueuedWork = {
  id: number;
  kind: string;
  payload: string;
  priority: number;
  status: string;
  assigned_worker_type: string | null;
  assigned_worker_id: number | null;
  result: string | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export const getWorkers = (limit = 50) =>
  apiGet<{ workers: Worker[]; load_balancer: LoadBalancerStatus; queue: QueuedWork[] }>(`/api/workers?limit=${limit}`);

export const getFinanceReport = (period: string, businessId?: number) =>
  apiGet<FinanceReport>(`/api/finance/report?period=${period}${businessId ? `&business_id=${businessId}` : ""}`);

export const getFinanceAll = (period: string) =>
  apiGet<{ period: string; reports: { business: Business; report: FinanceReport }[] }>(`/api/finance/all-businesses?period=${period}`);

export const getSecurityLatest = (businessId?: number) =>
  apiGet<{ latest_report: SecurityReport | null; recent_denied_calls: ToolCall[] }>(
    `/api/security/latest${businessId ? `?business_id=${businessId}` : ""}`
  );

export const getCosts = () => apiGet<{ cost_summary: CostRow[]; recent_tool_calls: ToolCall[] }>("/api/costs");

export type Site = {
  id: number;
  business_id: number;
  business_name: string;
  domain: string;
  template_id: string;
  status: string;
  local_path: string | null;
  file_exists: boolean;
};

export const getWebsites = () => apiGet<{ sites: Site[] }>("/api/websites");

export const getHealth = () =>
  apiGet<{ db_ok: boolean; ollama_host: string; allow_exec: boolean; dry_run: boolean; workspaces_dir: string }>("/api/health");

export type Bug = {
  id: number;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  source: string;
  file_path: string | null;
  function_name: string | null;
  module_name: string | null;
  line_number: number | null;
  root_cause: string | null;
  fix_recommendation: string | null;
  confidence: number | null;
  occurrence_count: number;
  duplicate_of: number | null;
  regression_count: number;
  created_at: string;
  updated_at: string;
};

export type BugEvent = { id: number; bug_id: number; event_type: string; payload: string; created_at: string };
export type Patch = {
  id: number;
  bug_id: number;
  target_file: string;
  full_file_path: string;
  diff_path: string | null;
  applied: number;
  created_at: string;
};

export const getBugs = (status?: string, severity?: string) => {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (severity) params.set("severity", severity);
  const qs = params.toString();
  return apiGet<{ bugs: Bug[] }>(`/api/bugs${qs ? `?${qs}` : ""}`);
};

export const getBugDetail = (id: number) => apiGet<{ bug: Bug; events: BugEvent[]; patches: Patch[] }>(`/api/bugs/detail?id=${id}`);

export type Audit = {
  id: number;
  status: string;
  severity_score: number | null;
  findings_count: number;
  files_affected: number;
  executive_summary: string | null;
  created_at: string;
  completed_at: string | null;
};

export type AuditFinding = {
  id: number;
  audit_id: number;
  category: string;
  severity: string;
  file_path: string | null;
  line_number: number | null;
  description: string;
  recommendation: string | null;
  bug_id: number | null;
};

export const getAudits = () => apiGet<{ audits: Audit[] }>("/api/audits");
export const getAuditDetail = (id: number) => apiGet<{ audit: Audit; findings: AuditFinding[] }>(`/api/audits/detail?id=${id}`);

export type Correction = {
  id: number;
  task_type: string;
  task_ref: string | null;
  business_id: number | null;
  status: string;
  correction_score: number | null;
  quality_score: number | null;
  issues_found: number;
  issues_fixed: number;
  qa_status: string | null;
  security_status: string | null;
  final_status: string | null;
  original_content: string | null;
  corrected_content: string | null;
  summary: string | null;
  created_at: string;
  completed_at: string | null;
};

export type CorrectionFinding = {
  id: number;
  correction_id: number;
  category: string;
  description: string;
  auto_fixed: number;
  created_at: string;
};

export const getCorrections = (limit = 20) => apiGet<{ corrections: Correction[] }>(`/api/corrections?limit=${limit}`);
export const getCorrectionDetail = (id: number) =>
  apiGet<{ correction: Correction; findings: CorrectionFinding[] }>(`/api/corrections/detail?id=${id}`);

export type PaymentLink = {
  id: number;
  razorpay_link_id: string;
  short_url: string;
  amount_inr: number;
  description: string;
  customer_name: string | null;
  customer_contact: string | null;
  reference_id: string | null;
  status: string;
  created_at: string;
  last_checked_at: string | null;
};

export const getPaymentLinks = (limit = 50) =>
  apiGet<{ payment_links: PaymentLink[]; total_paid_inr: number }>(`/api/payments?limit=${limit}`);

export type WebsiteReview = {
  id: number;
  url: string;
  business_id: number | null;
  status: string;
  seo_score: number | null;
  conversion_score: number | null;
  ui_score: number | null;
  deployment_ready: number;
  findings_count: number;
  summary: string | null;
  created_at: string;
  completed_at: string | null;
};

export type WebsiteReviewFinding = {
  id: number;
  review_id: number;
  category: string;
  severity: string;
  description: string;
  created_at: string;
};

export const getWebsiteReviews = (limit = 20) => apiGet<{ reviews: WebsiteReview[] }>(`/api/website-reviews?limit=${limit}`);
export const getWebsiteReviewDetail = (id: number) =>
  apiGet<{ review: WebsiteReview; findings: WebsiteReviewFinding[] }>(`/api/website-reviews/detail?id=${id}`);

export type GatewayActivity = { count: number; paid_count: number; last_used: string | null };
export const getGatewayActivity = () => apiGet<{ gateways: Record<string, GatewayActivity> }>("/api/gateway-activity");

export type HealthSnapshot = {
  id: number;
  cpu_percent: number;
  cpu_freq_mhz: number | null;
  cpu_temp_c: number | null;
  ram_percent: number;
  swap_percent: number;
  disk_percent: number;
  battery_percent: number | null;
  battery_plugged: number | null;
  internet_ok: number;
  ollama_ok: number;
  db_ok: number;
  active_tasks: number;
  untriaged_errors: number;
  health_score: number;
  performance_score: number;
  created_at: string;
};

export type ServiceStatus = { docker: string; claude: string; telegram: string; google_sheets: string };

export const getSentinelLatest = () => apiGet<{ snapshot: HealthSnapshot | null; services: ServiceStatus }>("/api/sentinel/latest");
export const getSentinelHistory = (limit = 50) => apiGet<{ snapshots: HealthSnapshot[] }>(`/api/sentinel/history?limit=${limit}`);

export type KnowledgeDoc = { id: number; category: string; title: string; content: string; tags: string; created_at: string; updated_at: string };
export const getKnowledge = (category?: string) => apiGet<{ documents: KnowledgeDoc[] }>(`/api/knowledge${category ? `?category=${category}` : ""}`);

export type VoiceCommand = {
  id: number;
  identity: string;
  raw_transcript: string;
  detected_language: string | null;
  language_confidence: number | null;
  routed_agent: string | null;
  routed_action: string | null;
  denied_reason: string | null;
  result_summary: string | null;
  created_at: string;
};
export const getVoiceRecent = () => apiGet<{ commands: VoiceCommand[] }>("/api/voice/recent");

export type FullTask = {
  id: number;
  tenant_id: string;
  business_id: number | null;
  agent_id: string;
  goal: string;
  status: string;
  risk_level: string;
  result: string | null;
  created_at: string;
};
export const getTasks = (status?: string) => apiGet<{ tasks: FullTask[]; counts: Record<string, number> }>(`/api/tasks${status ? `?status=${status}` : ""}`);

export type MemoryEntry = {
  id: number;
  tenant_id: string;
  layer: string;
  business_id: number | null;
  content: string;
  tags: string | null;
  created_at: string;
};
export const getMemory = (layer?: string) => apiGet<{ entries: MemoryEntry[] }>(`/api/memory${layer ? `?layer=${layer}` : ""}`);

export type WebsiteProject = {
  id: number;
  business_id: number | null;
  business_name: string;
  site_type: string;
  founder_request: string;
  requirements: string | null;
  status: string;
  qa_notes: string | null;
  security_score: number | null;
  site_id: number | null;
  deployment_package_path: string | null;
  created_at: string;
  updated_at: string;
};
export const getWebsiteProjects = (status?: string) =>
  apiGet<{ projects: WebsiteProject[]; templates: string[] }>(`/api/website-projects${status ? `?status=${status}` : ""}`);
