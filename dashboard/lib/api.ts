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

export const getDecisions = (limit = 20) => apiGet<{ decisions: Decision[] }>(`/api/ceo/decisions?limit=${limit}`);

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
