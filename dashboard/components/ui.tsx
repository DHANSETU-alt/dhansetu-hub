import { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`glass hud-card rounded-xl shadow-[0_1px_0_0_rgba(255,255,255,0.04)_inset] ${className}`}>{children}</div>;
}

export function CardHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 px-5 py-4 border-b border-[var(--border)]">
      <div>
        <h2 className="text-sm font-semibold tracking-wide text-[var(--ink)]">{title}</h2>
        {subtitle && <p className="text-xs text-[var(--muted-foreground)] mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function CardBody({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`p-5 ${className}`}>{children}</div>;
}

type BadgeTone = "local" | "cloud" | "good" | "warn" | "bad" | "neutral";

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: BadgeTone }) {
  const toneMap: Record<BadgeTone, string> = {
    local: "bg-[var(--local-soft)] text-[var(--local)]",
    cloud: "bg-[var(--cloud-soft)] text-[var(--cloud)]",
    good: "bg-[var(--local-soft)] text-[var(--good)]",
    warn: "bg-[var(--cloud-soft)] text-[var(--warn)]",
    bad: "bg-[color-mix(in_srgb,var(--bad)_18%,transparent)] text-[var(--bad)]",
    neutral: "bg-[var(--surface-2)] text-[var(--muted-foreground)]",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium tracking-wide uppercase ${toneMap[tone]}`}>
      {children}
    </span>
  );
}

export function StatTile({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: BadgeTone }) {
  const toneColor = tone === "bad" ? "var(--bad)" : tone === "warn" ? "var(--warn)" : tone === "good" ? "var(--good)" : "var(--ink)";
  return (
    <div className="glass hud-tile rounded-xl p-4">
      <div className="text-[11px] uppercase tracking-wide text-[var(--muted-foreground)]">{label}</div>
      <div className="mt-1 text-2xl font-semibold font-mono-num" style={{ color: toneColor }}>
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-[var(--muted-foreground)]">{hint}</div>}
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="text-sm text-[var(--muted-foreground)] py-6 text-center">{children}</div>;
}

export function ComingSoon({ title, note }: { title: string; note: string }) {
  return (
    <Card>
      <CardHeader title={title} subtitle="Not built yet" />
      <CardBody>
        <p className="text-sm text-[var(--muted-foreground)] max-w-[60ch]">{note}</p>
      </CardBody>
    </Card>
  );
}
