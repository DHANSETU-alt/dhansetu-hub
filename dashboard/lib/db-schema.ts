// Database schema for Founder Dashboard workspaces
// This defines the structure for storing founder workspace preferences and session data

export interface FounderWorkspace {
  id: string;
  userId: string;
  name: string;
  type: WorkspaceType;
  description?: string;
  isDefault: boolean;
  layout: WorkspaceLayout;
  refreshInterval: number; // seconds
  lastAccessedAt: string;
  createdAt: string;
  updatedAt: string;
}

export interface WorkspaceLayout {
  columns: number;
  showMetrics: string[];
  widgetPositions: Record<string, { x: number; y: number; w: number; h: number }>;
  theme?: "light" | "dark";
}

export type WorkspaceType =
  | "overview"
  | "budget"
  | "payment"
  | "research"
  | "content"
  | "peopledesk"
  | "partners"
  | "knowledge"
  | "security"
  | "agents"
  | "settings"
  | "analytics";

export interface FounderDashboardSession {
  id: string;
  userId: string;
  activeWorkspace: WorkspaceType;
  sessionData: Record<string, unknown>;
  lastActivity: string;
  expiresAt: string;
}

export interface WorkspaceMetrics {
  workspaceId: string;
  timestamp: string;
  viewCount: number;
  actionCount: number;
  dataRefreshCount: number;
  averageResponseTime: number; // ms
}

// SQL Migration to create founder_workspaces table
export const FOUNDER_WORKSPACES_MIGRATION = `
CREATE TABLE IF NOT EXISTS founder_workspaces (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  description TEXT,
  is_default BOOLEAN DEFAULT FALSE,
  layout JSONB NOT NULL,
  refresh_interval INTEGER DEFAULT 30,
  last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, name),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_founder_workspaces_user_id ON founder_workspaces(user_id);
CREATE INDEX idx_founder_workspaces_type ON founder_workspaces(type);
CREATE INDEX idx_founder_workspaces_default ON founder_workspaces(is_default) WHERE is_default = TRUE;
`;

// SQL Migration to create founder_dashboard_sessions table
export const FOUNDER_DASHBOARD_SESSIONS_MIGRATION = `
CREATE TABLE IF NOT EXISTS founder_dashboard_sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  active_workspace TEXT NOT NULL,
  session_data JSONB DEFAULT '{}',
  last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (active_workspace) REFERENCES founder_workspaces(type)
);

CREATE INDEX idx_founder_dashboard_sessions_user_id ON founder_dashboard_sessions(user_id);
CREATE INDEX idx_founder_dashboard_sessions_expires_at ON founder_dashboard_sessions(expires_at);
`;

// SQL Migration to create workspace_metrics table
export const WORKSPACE_METRICS_MIGRATION = `
CREATE TABLE IF NOT EXISTS workspace_metrics (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  view_count INTEGER DEFAULT 0,
  action_count INTEGER DEFAULT 0,
  data_refresh_count INTEGER DEFAULT 0,
  average_response_time INTEGER DEFAULT 0,
  FOREIGN KEY (workspace_id) REFERENCES founder_workspaces(id)
);

CREATE INDEX idx_workspace_metrics_workspace_id ON workspace_metrics(workspace_id);
CREATE INDEX idx_workspace_metrics_timestamp ON workspace_metrics(timestamp);
`;

// Default workspace layout configurations
export const DEFAULT_WORKSPACE_LAYOUTS: Record<WorkspaceType, WorkspaceLayout> = {
  overview: {
    columns: 2,
    showMetrics: ["systemHealth", "revenue", "taskQueue", "quickActions"],
    widgetPositions: {
      systemHealth: { x: 0, y: 0, w: 2, h: 1 },
      revenue: { x: 0, y: 1, w: 2, h: 1 },
      taskQueue: { x: 0, y: 2, w: 1, h: 1 },
      quickActions: { x: 1, y: 2, w: 1, h: 1 },
    },
  },
  budget: {
    columns: 2,
    showMetrics: ["incomeExpenses", "categories", "alerts", "settings"],
    widgetPositions: {
      incomeExpenses: { x: 0, y: 0, w: 2, h: 1 },
      categories: { x: 0, y: 1, w: 2, h: 1 },
      alerts: { x: 0, y: 2, w: 2, h: 1 },
      settings: { x: 0, y: 3, w: 2, h: 1 },
    },
  },
  payment: {
    columns: 1,
    showMetrics: ["summary", "orderHistory", "failedOrders", "settings"],
    widgetPositions: {
      summary: { x: 0, y: 0, w: 1, h: 1 },
      orderHistory: { x: 0, y: 1, w: 1, h: 2 },
      failedOrders: { x: 0, y: 3, w: 1, h: 1 },
      settings: { x: 0, y: 4, w: 1, h: 1 },
    },
  },
  research: {
    columns: 1,
    showMetrics: ["jobsSummary", "jobQueue", "controls"],
    widgetPositions: {
      jobsSummary: { x: 0, y: 0, w: 1, h: 1 },
      jobQueue: { x: 0, y: 1, w: 1, h: 2 },
      controls: { x: 0, y: 3, w: 1, h: 1 },
    },
  },
  content: {
    columns: 1,
    showMetrics: ["summary", "queue", "distribution", "actions"],
    widgetPositions: {
      summary: { x: 0, y: 0, w: 1, h: 1 },
      queue: { x: 0, y: 1, w: 1, h: 2 },
      distribution: { x: 0, y: 3, w: 1, h: 1 },
      actions: { x: 0, y: 4, w: 1, h: 1 },
    },
  },
  peopledesk: {
    columns: 1,
    showMetrics: ["tickets", "metrics", "recentTickets", "actions"],
    widgetPositions: {
      tickets: { x: 0, y: 0, w: 1, h: 1 },
      metrics: { x: 0, y: 1, w: 1, h: 1 },
      recentTickets: { x: 0, y: 2, w: 1, h: 2 },
      actions: { x: 0, y: 4, w: 1, h: 1 },
    },
  },
  partners: {
    columns: 1,
    showMetrics: ["summary", "partnerList", "commission", "actions"],
    widgetPositions: {
      summary: { x: 0, y: 0, w: 1, h: 1 },
      partnerList: { x: 0, y: 1, w: 1, h: 2 },
      commission: { x: 0, y: 3, w: 1, h: 1 },
      actions: { x: 0, y: 4, w: 1, h: 1 },
    },
  },
  knowledge: {
    columns: 1,
    showMetrics: ["summary", "search", "popular", "categories", "actions"],
    widgetPositions: {
      summary: { x: 0, y: 0, w: 1, h: 1 },
      search: { x: 0, y: 1, w: 1, h: 1 },
      popular: { x: 0, y: 2, w: 1, h: 2 },
      categories: { x: 0, y: 4, w: 1, h: 1 },
      actions: { x: 0, y: 5, w: 1, h: 1 },
    },
  },
  security: {
    columns: 1,
    showMetrics: ["status", "assessment", "events", "compliance", "actions"],
    widgetPositions: {
      status: { x: 0, y: 0, w: 1, h: 1 },
      assessment: { x: 0, y: 1, w: 1, h: 1 },
      events: { x: 0, y: 2, w: 1, h: 2 },
      compliance: { x: 0, y: 4, w: 1, h: 1 },
      actions: { x: 0, y: 5, w: 1, h: 1 },
    },
  },
  agents: {
    columns: 2,
    showMetrics: ["summary", "delegation", "activeAgents", "performance", "actions"],
    widgetPositions: {
      summary: { x: 0, y: 0, w: 2, h: 1 },
      delegation: { x: 0, y: 1, w: 2, h: 1 },
      activeAgents: { x: 0, y: 2, w: 2, h: 2 },
      performance: { x: 0, y: 4, w: 2, h: 1 },
      actions: { x: 0, y: 5, w: 2, h: 1 },
    },
  },
  settings: {
    columns: 1,
    showMetrics: ["account", "notifications", "apiKeys", "integrations", "privacy"],
    widgetPositions: {
      account: { x: 0, y: 0, w: 1, h: 1 },
      notifications: { x: 0, y: 1, w: 1, h: 1 },
      apiKeys: { x: 0, y: 2, w: 1, h: 1 },
      integrations: { x: 0, y: 3, w: 1, h: 1 },
      privacy: { x: 0, y: 4, w: 1, h: 1 },
    },
  },
  analytics: {
    columns: 1,
    showMetrics: ["dateRange", "metrics", "trends", "topPages", "traffic", "goals", "export"],
    widgetPositions: {
      dateRange: { x: 0, y: 0, w: 1, h: 1 },
      metrics: { x: 0, y: 1, w: 1, h: 1 },
      trends: { x: 0, y: 2, w: 1, h: 1 },
      topPages: { x: 0, y: 3, w: 1, h: 1 },
      traffic: { x: 0, y: 4, w: 1, h: 1 },
      goals: { x: 0, y: 5, w: 1, h: 1 },
      export: { x: 0, y: 6, w: 1, h: 1 },
    },
  },
};
