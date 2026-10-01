"use client";

import { useState, useEffect } from "react";
import { Card, CardHeader, CardBody, Badge, StatTile } from "@/components/ui";
import OverviewWorkspace from "@/components/workspaces/OverviewWorkspace";
import SmartBudgetWorkspace from "@/components/workspaces/SmartBudgetWorkspace";
import PaymentWorkspace from "@/components/workspaces/PaymentWorkspace";
import ResearchWorkspace from "@/components/workspaces/ResearchWorkspace";
import ContentWorkspace from "@/components/workspaces/ContentWorkspace";
import PeopleDeskWorkspace from "@/components/workspaces/PeopleDeskWorkspace";
import PartnerNetworkWorkspace from "@/components/workspaces/PartnerNetworkWorkspace";
import KnowledgeBaseWorkspace from "@/components/workspaces/KnowledgeBaseWorkspace";
import SecurityWorkspace from "@/components/workspaces/SecurityWorkspace";
import AgentsWorkspace from "@/components/workspaces/AgentsWorkspace";
import SettingsWorkspace from "@/components/workspaces/SettingsWorkspace";
import AnalyticsWorkspace from "@/components/workspaces/AnalyticsWorkspace";

type WorkspaceId =
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

const WORKSPACES: Array<{ id: WorkspaceId; label: string; icon: string }> = [
  { id: "overview", label: "Overview", icon: "📊" },
  { id: "budget", label: "SmartBudget", icon: "💰" },
  { id: "payment", label: "Payment", icon: "💳" },
  { id: "research", label: "Research", icon: "🔬" },
  { id: "content", label: "Content", icon: "📝" },
  { id: "peopledesk", label: "PeopleDesk", icon: "👥" },
  { id: "partners", label: "Partners", icon: "🤝" },
  { id: "knowledge", label: "Knowledge", icon: "📚" },
  { id: "security", label: "Security", icon: "🔒" },
  { id: "agents", label: "Agents", icon: "🤖" },
  { id: "settings", label: "Settings", icon: "⚙️" },
  { id: "analytics", label: "Analytics", icon: "📈" },
];

export default function FounderDashboard() {
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceId>("overview");
  const [isAutoRefresh, setIsAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30);

  // Auto-refresh workspace data based on interval
  useEffect(() => {
    if (!isAutoRefresh) return;
    const timer = setInterval(() => {
      // Trigger refresh by updating a key in workspace components
      window.dispatchEvent(new CustomEvent("workspace-refresh"));
    }, refreshInterval * 1000);
    return () => clearInterval(timer);
  }, [isAutoRefresh, refreshInterval]);

  const renderWorkspace = () => {
    switch (activeWorkspace) {
      case "overview":
        return <OverviewWorkspace />;
      case "budget":
        return <SmartBudgetWorkspace />;
      case "payment":
        return <PaymentWorkspace />;
      case "research":
        return <ResearchWorkspace />;
      case "content":
        return <ContentWorkspace />;
      case "peopledesk":
        return <PeopleDeskWorkspace />;
      case "partners":
        return <PartnerNetworkWorkspace />;
      case "knowledge":
        return <KnowledgeBaseWorkspace />;
      case "security":
        return <SecurityWorkspace />;
      case "agents":
        return <AgentsWorkspace />;
      case "settings":
        return <SettingsWorkspace />;
      case "analytics":
        return <AnalyticsWorkspace />;
      default:
        return <OverviewWorkspace />;
    }
  };

  const activeWorkspaceLabel =
    WORKSPACES.find((w) => w.id === activeWorkspace)?.label || "Overview";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-1">
            Founder Dashboard
          </h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            12 workspaces for CEO judgment calls, agent oversight, and delegation
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsAutoRefresh(!isAutoRefresh)}
            className="cursor-pointer hover:opacity-90 transition"
          >
            <Badge tone={isAutoRefresh ? "good" : "neutral"}>
              {isAutoRefresh ? `Auto-refresh: ${refreshInterval}s` : "Manual"}
            </Badge>
          </button>
        </div>
      </div>

      {/* Workspace Selector Tabs */}
      <div className="flex flex-wrap gap-2 p-3 bg-[var(--surface-1)] rounded-xl border border-[var(--border)]">
        {WORKSPACES.map((workspace) => (
          <button
            key={workspace.id}
            onClick={() => setActiveWorkspace(workspace.id)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
              activeWorkspace === workspace.id
                ? "bg-[var(--local)] text-white shadow-lg"
                : "bg-[var(--surface-2)] text-[var(--ink)] hover:bg-[var(--surface-3)]"
            }`}
          >
            <span className="mr-1">{workspace.icon}</span>
            {workspace.label}
          </button>
        ))}
      </div>

      {/* Breadcrumb Navigation */}
      <div className="text-xs text-[var(--muted-foreground)] flex items-center gap-2">
        <span>Founder Dashboard</span>
        <span className="text-[var(--border)]">›</span>
        <span className="font-medium text-[var(--ink)]">{activeWorkspaceLabel}</span>
      </div>

      {/* Main Workspace Content */}
      <div className="space-y-4">
        {renderWorkspace()}
      </div>

      {/* Auto-Refresh Settings Card */}
      <Card>
        <CardHeader title="Refresh Settings" subtitle="Configure real-time data updates" />
        <CardBody>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[5, 10, 30, 60].map((seconds) => (
              <button
                key={seconds}
                onClick={() => setRefreshInterval(seconds)}
                className={`p-3 rounded-lg border transition-all ${
                  refreshInterval === seconds
                    ? "border-[var(--local)] bg-[var(--local-soft)] text-[var(--local)] font-medium"
                    : "border-[var(--border)] text-[var(--muted-foreground)] hover:border-[var(--local)]"
                }`}
              >
                {seconds}s
              </button>
            ))}
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
