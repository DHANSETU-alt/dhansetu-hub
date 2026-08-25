"use client";

import { useState } from "react";
import Link from "next/link";

// Stage 1 (Business Discovery) only -- see orchestrator/onboarding.py.
// Field order/labels match the founder's own spec exactly.
const FIELDS: { key: string; label: string; required?: boolean; placeholder?: string }[] = [
  { key: "business_name", label: "Business Name", required: true },
  { key: "industry", label: "Industry" },
  { key: "website", label: "Website" },
  { key: "business_model", label: "Business Model" },
  { key: "target_customer", label: "Target Customer" },
  { key: "revenue_streams", label: "Primary Revenue Streams" },
  { key: "team_size", label: "Current Team Size" },
  { key: "monthly_revenue_range", label: "Monthly Revenue Range" },
  { key: "main_challenges", label: "Main Business Challenges" },
  { key: "preferred_tools", label: "Preferred Tools" },
  { key: "current_software", label: "Current Software" },
  { key: "growth_goal_12mo", label: "Growth Goal (Next 12 Months)" },
];

const CATEGORY_LABELS: Record<string, string> = {
  revenue_bottlenecks: "Revenue Bottlenecks",
  operational_bottlenecks: "Operational Bottlenecks",
  marketing_bottlenecks: "Marketing Bottlenecks",
  sales_bottlenecks: "Sales Bottlenecks",
  support_bottlenecks: "Customer Support Bottlenecks",
};

export default function BlackboxOnboardingPage() {
  const [values, setValues] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState("");
  const [result, setResult] = useState<Record<string, string | null> | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!values.business_name?.trim()) {
      setError("Business Name is required.");
      setStatus("error");
      return;
    }
    setStatus("loading");
    setError("");
    setResult(null);
    try {
      const res = await fetch("/api/onboarding/discovery", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values),
      });
      const data = await res.json();
      if (!res.ok && res.status !== 202) throw new Error(data.error || `Request failed (${res.status})`);
      if (data.error) { setError(data.error); }
      setResult(data);
      setStatus("idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setStatus("error");
    }
  }

  return (
    <div className="fixed inset-0 overflow-y-auto" style={{ background: "#0a0c10", color: "#e8ecf1" }}>
      <div className="max-w-2xl mx-auto px-8 py-10">
        <Link href="/blackboxops-os" className="text-xs font-mono text-[#8b95a6] hover:text-white">← blackboxOps_OS</Link>
        <h1 className="text-3xl font-semibold mt-4 mb-2">AI Employee Onboarding — Business Discovery</h1>
        <p className="text-sm text-[#a8b1c2] mb-8">
          Stage 1 only, real and working: tell us about your business, and get a real analysis of where your
          revenue, operations, marketing, sales, and support are actually stuck — grounded in what you tell us,
          not generic advice. Later stages (AI employee generation, KPI dashboards, automation) come after this.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {FIELDS.map((f) => (
            <div key={f.key}>
              <label className="block text-xs uppercase tracking-wide text-[#8b95a6] mb-1.5">
                {f.label}{f.required && <span style={{ color: "#dba956" }}> *</span>}
              </label>
              <input
                type="text"
                value={values[f.key] || ""}
                onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                className="w-full rounded-lg border border-[#2a3040] bg-[#0f131a] px-3 py-2 text-sm text-[#e8ecf1]"
              />
            </div>
          ))}

          {error && <p className="text-xs" style={{ color: "#f87171" }}>{error}</p>}

          <button
            type="submit"
            disabled={status === "loading"}
            className="rounded-lg px-5 py-2.5 text-sm font-medium disabled:opacity-50"
            style={{ background: "#dba956", color: "#0a0c10" }}
          >
            {status === "loading" ? "Analyzing (real local-model call, can take a minute)…" : "Submit & Analyze"}
          </button>
        </form>

        {result && (
          <div className="mt-10 rounded-xl border border-[#1e232e] p-6" style={{ background: "#0f131a" }}>
            <div className="text-xs font-mono uppercase tracking-wide mb-4" style={{ color: "#dba956" }}>
              Findings — discovery #{result.id}
            </div>
            <div className="space-y-4">
              {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                <div key={key}>
                  <div className="text-sm font-medium mb-1">{label}</div>
                  <p className="text-sm text-[#a8b1c2] leading-relaxed">
                    {result[key] || <span className="italic text-[#5b6472]">not enough information given</span>}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
