"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = { href: string; label: string; soon?: boolean };

const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: "Overview",
    items: [{ href: "/", label: "Executive Dashboard" }],
  },
  {
    group: "Governance",
    items: [
      { href: "/ceo", label: "CEO Dashboard" },
      { href: "/finance", label: "Finance Dashboard" },
      { href: "/security", label: "Security Dashboard" },
      { href: "/bugs", label: "Bug Dashboard" },
      { href: "/audits", label: "Audit History" },
      { href: "/correction", label: "Correction Bot" },
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
      { href: "/agent-health", label: "Agent Health Monitor", soon: true },
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
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <nav className="glass w-60 shrink-0 border-r-0 h-screen sticky top-0 overflow-y-auto">
      <div className="px-4 py-5 border-b border-[var(--border)]">
        <div className="text-sm font-semibold tracking-tight">SHAKTHI AI OS</div>
        <div className="text-[11px] text-[var(--muted-foreground)] mt-0.5">Founder Control Center</div>
      </div>
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
