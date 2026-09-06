import Link from "next/link";
import { LivingSystemBackground } from "@/components/LivingSystemBackground";
import { SUPPORT_EMAIL } from "@/lib/brand";

const NAV = [
  { href: "/blackboxops-os", label: "Home" },
  { href: "/blackboxops-os/onboarding", label: "AI Employee Onboarding" },
  { href: "/blackboxops-os/command-center", label: "Command Center" },
  { href: "/blackboxops-os/agents", label: "Agent Visualization" },
  { href: "/blackboxops-os/ert", label: "ERT Center" },
  { href: "/blackboxops-os/pricing", label: "Pricing" },
  { href: "/blackboxops-os/portal", label: "Customer Portal" },
];

const FEATURES = [
  { name: "CEO", desc: "Every risky decision gets a reasoned judgment call, scored and logged — never a silent approval." },
  { name: "Sentinel", desc: "Continuous health monitoring — CPU, RAM, disk, services — before small problems become outages." },
  { name: "Security", desc: "Deterministic scans for exposed secrets, risky permissions, and misconfiguration — not guesswork." },
  { name: "Finance", desc: "Real revenue, cost, and margin tracking across every business you run." },
  { name: "Chrome Developer", desc: "Real browser-driven audits — SEO, performance, conversion — not just HTML parsing." },
  { name: "Website Builder", desc: "From founder request to a packaged, reviewed site — CEO and Security approved before it ships." },
  { name: "Worker Pool", desc: "Parallel execution that scales with load, so nothing queues behind a single slow task." },
  { name: "ERT", desc: "Every incident gets an owner, a backup, an escalation path, and a postmortem — automatically." },
];

export default function BlackboxHomePage() {
  return (
    <div className="fixed inset-0 overflow-y-auto" style={{ color: "#e8ecf1" }}>
      <LivingSystemBackground />
      <div className="max-w-5xl mx-auto px-8 py-10">
        <nav className="flex items-center justify-between mb-16">
          <div className="font-mono text-sm tracking-wide">
            <span style={{ color: "#dba956" }}>BLACKBOX</span>_OS
          </div>
          <div className="flex items-center gap-6 text-xs font-mono text-[#8b95a6]">
            {NAV.slice(1).map((n) => (
              <Link key={n.href} href={n.href} className="hover:text-white transition-colors">{n.label}</Link>
            ))}
          </div>
        </nav>

        <header className="max-w-2xl mb-20">
          <div className="text-xs font-mono uppercase tracking-[0.2em] mb-4" style={{ color: "#dba956" }}>
            UNDER REVIEW · HOLD FOR LAUNCH 🚀 — FULL TESTING MODE
          </div>
          <h1 className="text-4xl md:text-5xl font-semibold leading-tight mb-5" style={{ letterSpacing: "-0.01em" }}>
            AI-assisted operations for small agencies —
            <br />with a full team of agents behind it.
          </h1>
          <p className="text-lg text-[#a8b1c2] leading-relaxed">
            Client reporting, lead follow-up, and task handoffs, backed by CEO approval gates, live health monitoring,
            security scanning, and an Emergency Response Team that never leaves an incident untracked.
            Human approval and clear guardrails, the way it always has been — now with the full agent network visible.
          </p>
          <div className="flex gap-3 mt-8">
            <Link href="/blackboxops-os/pricing" className="rounded-lg px-5 py-2.5 text-sm font-medium" style={{ background: "#dba956", color: "#0a0c10" }}>
              View Pricing
            </Link>
            <Link href="/blackboxops-os/agents" className="rounded-lg px-5 py-2.5 text-sm font-medium border border-[#2a3040] text-[#e8ecf1]">
              See the Agent Network Live
            </Link>
          </div>
        </header>

        <section className="mb-20">
          <div className="text-xs font-mono uppercase tracking-[0.15em] text-[#8b95a6] mb-6">The Team Running Your Operations</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {FEATURES.map((f) => (
              <div key={f.name} className="rounded-xl border border-[#1e232e] p-5" style={{ background: "#0f131a" }}>
                <div className="font-mono text-sm mb-1.5" style={{ color: "#dba956" }}>{f.name}</div>
                <p className="text-sm text-[#a8b1c2] leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <footer className="border-t border-[#1e232e] pt-8 pb-16 text-xs font-mono text-[#8b95a6]">
          Powered by <span className="text-[#e8ecf1]">GVC_INC</span>
          <span className="mx-2">·</span>
          <a href={`mailto:${SUPPORT_EMAIL}`} className="hover:text-white">{SUPPORT_EMAIL}</a>
          <span className="mx-2">·</span>
          <Link href="/" className="hover:text-white">SHAKTHI OS internal dashboard</Link>
        </footer>
      </div>
    </div>
  );
}
