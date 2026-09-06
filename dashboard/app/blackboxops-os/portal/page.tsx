import Link from "next/link";
import { SUPPORT_EMAIL } from "@/lib/brand";

export default function BlackboxPortalPage() {
  return (
    <div className="fixed inset-0 overflow-y-auto" style={{ background: "#0a0c10", color: "#e8ecf1" }}>
      <div className="max-w-2xl mx-auto px-8 py-10">
        <Link href="/blackboxops-os" className="text-xs font-mono text-[#8b95a6] hover:text-white">← blackboxOps_OS</Link>
        <h1 className="text-3xl font-semibold mt-4 mb-2">Customer Portal</h1>
        <div className="rounded-xl border border-[#dba956]/40 p-6 mt-6" style={{ background: "#0f131a" }}>
          <div className="text-xs font-mono uppercase tracking-wide mb-3" style={{ color: "#dba956" }}>Not built — scoped honestly, not faked</div>
          <p className="text-sm text-[#a8b1c2] leading-relaxed mb-3">
            Every other blackboxOps_OS page reuses something real: Command Center and ERT Center read the live database,
            Agent Visualization is the actual Mission Control component, Pricing calls the actual Razorpay/PayU
            integrations. A Customer Portal needs something none of those do — <strong className="text-[#e8ecf1]">real user
            accounts</strong>: signup, login, sessions, password reset, and a way to tie a logged-in customer to their
            own subscription and usage data.
          </p>
          <p className="text-sm text-[#a8b1c2] leading-relaxed mb-3">
            Nothing in this project has that today. <code className="text-xs bg-[#0a0c10] px-1.5 py-0.5 rounded">product_usage</code> and{" "}
            <code className="text-xs bg-[#0a0c10] px-1.5 py-0.5 rounded">product_subscriptions</code> (built for PDF
            Studio&apos;s pricing) key on email address only — good enough for a usage gate, not enough for a real
            login-protected account page a customer could return to.
          </p>
          <p className="text-sm text-[#a8b1c2] leading-relaxed">
            This is a real, separate feature — auth is its own scoped piece of work, not a checkbox on this page.
            Flagging it here rather than shipping a fake login form that doesn&apos;t actually protect anything.
          </p>
        </div>
        <p className="text-sm text-[#8b95a6] mt-6">
          Need help with your account in the meantime? Email{" "}
          <a href={`mailto:${SUPPORT_EMAIL}`} className="text-[#dba956] hover:underline">{SUPPORT_EMAIL}</a> — a real
          person reads it, not a bot.
        </p>
      </div>
    </div>
  );
}
