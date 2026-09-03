"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AngellaPresence } from "@/components/AngellaPresence";
import { SHAKTHI_OS_VERSION } from "@/lib/version";
import type { PaAngellaStatus } from "@/lib/api";

type NavItem = { href: string; label: string; soon?: boolean };

const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: "Overview",
    items: [
      { href: "/", label: "Executive Dashboard" },
      { href: "/command-center", label: "Founder Command Center" },
      { href: "/initiatives", label: "Founder Tasks" },
      { href: "/mission-control", label: "Mission Control" },
    ],
  },
  {
    group: "Governance",
    items: [
      { href: "/ceo", label: "CEO Dashboard" },
      { href: "/finance", label: "Finance Dashboard" },
      { href: "/payments", label: "Payments" },
      { href: "/security", label: "Security Dashboard" },
      { href: "/bugs", label: "Bug Dashboard" },
      { href: "/ert", label: "ERT Command Center" },
      { href: "/audits", label: "Audit History" },
      { href: "/control-plane-31", label: "Control Plane 3.1" },
      { href: "/correction", label: "Correction Bot" },
      { href: "/failure-analyses", label: "Failure Analysis Engine" },
      { href: "/chrome-developer", label: "Chrome Developer" },
    ],
  },
  {
    group: "Operations",
    items: [
      { href: "/agents", label: "Agent Registry" },
      { href: "/sentinel", label: "Sentinel" },
      { href: "/voice", label: "Voice Commander" },
      { href: "/costs", label: "Cost Ledger" },
      { href: "/tasks", label: "Task Pipeline" },
      { href: "/workers", label: "Worker Pool" },
      { href: "/agent-health", label: "Agent Health Monitor" },
    ],
  },
  {
    group: "Knowledge",
    items: [
      { href: "/memory", label: "Memory Explorer" },
      { href: "/knowledge", label: "Knowledge Explorer" },
    ],
  },
  {
    group: "Business",
    items: [
      { href: "/businesses", label: "Workspace Manager", soon: true },
      { href: "/website-builder", label: "Website Builder" },
      { href: "/websites", label: "Website Monitoring" },
      { href: "/website-health", label: "Website Health Watcher" },
      { href: "/client-success", label: "Client Success" },
      { href: "/pdf-studio", label: "Dhansetu PDF Studio", soon: true },
      { href: "/peopledesk", label: "Dhansetu PeopleDesk", soon: true },
      { href: "/trading", label: "Trading OS (paper)" },
      { href: "/dhansetu-ai", label: "Dhansetu AI" },
    ],
  },
];

export function Sidebar({ angellaStatus }: { angellaStatus?: PaAngellaStatus | null }) {
  const pathname = usePathname();
  return (
    <nav className="glass w-60 shrink-0 border-r-0 h-screen sticky top-0 overflow-y-auto relative z-20">
      <div className="px-4 py-5 border-b border-[var(--border)]">
        <div className="text-sm font-semibold tracking-tight">SHAKTHI AI OS</div>
        <div className="text-[11px] text-[var(--muted-foreground)] mt-0.5">Founder Control Center</div>
        <div
          className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-2 py-0.5 text-[10px] font-mono-num text-[var(--muted-foreground)]"
          title={`${SHAKTHI_OS_VERSION.codename} · commit ${SHAKTHI_OS_VERSION.gitCommit} · ${SHAKTHI_OS_VERSION.environment}`}
        >
          <span className="text-[var(--ink)] font-semibold">{SHAKTHI_OS_VERSION.osName}</span>
          <span>v{SHAKTHI_OS_VERSION.version}</span>
          <span className="opacity-60">&bull;</span>
          <span className="uppercase tracking-wide">{SHAKTHI_OS_VERSION.environment}</span>
        </div>
      </div>
      <AngellaPresence status={angellaStatus ?? null} />
      <div className="py-3">
        {NAV.map((section) => (
          <div key={section.group} className="mb-3">
            <div className="px-4 py-1 text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">{section.group}</div>
            {section.items.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center justify-between px-4 py-1.5 text-sm ${
                    active
                      ? "text-[var(--ink)] bg-[var(--surface-2)] border-l-2 border-[var(--local)]"
                      : "text-[var(--muted-foreground)] hover:text-[var(--ink)] border-l-2 border-transparent"
                  }`}
                >
                  <span>{item.label}</span>
                  {item.soon && (
                    <span className="text-[9px] uppercase tracking-wide text-[var(--muted-foreground)] bg-[var(--surface-2)] rounded px-1.5 py-0.5">
                      soon
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </div>
    </nav>
  );
}
