"use client";

import { jsPDF } from "jspdf";
import { FormEvent, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import "./seo-audit.css";

type Finding = { id: string; title: string; detail: string; fix: string; severity: "high" | "medium" | "low"; points: number };
type Passed = { id: string; title: string; detail: string; points: number };
type Report = { score: number; issues: Finding[]; passed: Passed[]; meta: { finalUrl: string; responseStatus: number; responseTimeMs: number; checks: number; linksChecked: number; generatedAt: string } };

const steps = ["Validate public target", "Read HTML structure", "Check links and discovery files", "Calculate observed score"];

export default function SeoAuditPage() {
  const [url, setUrl] = useState("https://dhansetuhub.in");
  const [report, setReport] = useState<Report | null>(null);
  const [running, setRunning] = useState(false);
  const [step, setStep] = useState(0);
  const [message, setMessage] = useState("");

  async function runAudit(event: FormEvent) {
    event.preventDefault();
    setRunning(true); setReport(null); setMessage(""); setStep(0);
    const timer = window.setInterval(() => setStep((current) => Math.min(current + 1, steps.length - 1)), 850);
    try {
      const response = await fetch("/api/seo-audit", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ url }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "The public audit could not be completed.");
      setReport(data as Report); setStep(steps.length - 1);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The audit could not be completed.");
    } finally {
      window.clearInterval(timer); setRunning(false);
    }
  }

  function downloadReport() {
    if (!report) return;
    const pdf = new jsPDF();
    const lines = [`DhanSetuHub SEO Audit`, `Target: ${report.meta.finalUrl}`, `Score: ${report.score}/100`, `Generated: ${new Date(report.meta.generatedAt).toLocaleString("en-IN")}`, ``, `Issues (${report.issues.length})`];
    report.issues.forEach((item) => lines.push(`[${item.severity.toUpperCase()}] ${item.title}`, item.detail, `Fix: ${item.fix}`, ""));
    lines.push(`Passed checks (${report.passed.length})`);
    report.passed.forEach((item) => lines.push(`- ${item.title}: ${item.detail}`));
    const wrapped = pdf.splitTextToSize(lines.join("\n"), 178);
    pdf.setFont("helvetica", "normal"); pdf.setFontSize(10); pdf.text(wrapped, 16, 18);
    pdf.save(`dhansetu-seo-audit-${new URL(report.meta.finalUrl).hostname}.pdf`);
  }

  return <main className="seo-page"><div className="seo-shell"><Header /><section className="seo-hero"><div><div className="seo-eyebrow">DhanSetu internal tool / free passive audit</div><h1>See what search engines <span className="seo-gradient">can read.</span></h1><p className="seo-lede">An original, transparent SEO audit for students, offices, and small businesses. It reads public HTML, discovery files, internal links, and response timing—without Seomator, tokens, signup, or hidden scoring.</p><div className="seo-hero-actions"><Link className="seo-button" href="#audit">Start a free audit <span aria-hidden="true">↓</span></Link><Link className="seo-button secondary" href="/portfolio">View the portfolio</Link></div><div className="seo-proof"><span>public evidence only</span><span>server-bounded</span><span>PDF report</span></div></div><div className="seo-orbit" aria-label="SEO audit routing visualization"><div className="seo-orbit-grid" aria-hidden="true" /><div className="seo-orbit-core"><div><strong>{report ? `${report.score}` : "SEO"}</strong><small>{report ? "observed score / 100" : "route → inspect → report"}</small></div></div><div className="seo-orbit-label">DhanSetu / audit brain<br />no external handoff</div><div className="seo-console"><span>$ audit public-page</span><span>→ checking metadata, links, indexability</span><span>✓ report stays in your workflow</span></div></div></section><section id="audit" className="audit-panel" aria-labelledby="audit-title"><div className="audit-panel-head"><div><div className="seo-eyebrow">Live routing layer</div><h2 id="audit-title">Run the internal audit.</h2><p>Only public HTTP/HTTPS targets are accepted. Private addresses, oversized pages, and redirect abuse are rejected.</p></div>{report && <button className="seo-button secondary no-print" type="button" onClick={downloadReport}>Download report ↓</button>}</div><form className="audit-form no-print" onSubmit={runAudit}><label className="audit-input" htmlFor="seo-target"><span aria-hidden="true">https://</span><input id="seo-target" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="example.com" required /></label><button className="seo-button" type="submit" disabled={running}>{running ? "Auditing…" : "Analyze public page →"}</button></form>{running && <div className="route-strip" role="status" aria-live="polite"><span className="route-dot" aria-hidden="true" />{steps[step]}…</div>}{message && <p className="audit-note error" role="alert">{message}</p>}{report && <div className="report-grid"><article className="report-card score-card"><div className="score-ring" style={{ "--score": report.score } as React.CSSProperties}><div className="score-value"><strong>{report.score}</strong><small>observed score</small></div></div><div className="score-meta">{report.meta.responseStatus} response · {report.meta.responseTimeMs} ms<br />{report.meta.linksChecked} internal links checked</div></article><article className="report-card"><h3>Issues to fix · {report.issues.length}</h3><div className="finding-list">{report.issues.length ? report.issues.map((item) => <div className="finding" key={item.id}><div className="finding-title"><span>{item.title}</span><span className={`badge ${item.severity}`}>{item.severity}</span></div><div className="finding-detail">{item.detail}</div><div className="finding-fix">Fix → {item.fix}</div></div>) : <p className="empty-state">No issues were observed in the bounded checks.</p>}</div></article><article className="report-card"><h3>Passed checks · {report.passed.length}</h3><ul className="passed-list">{report.passed.map((item) => <li key={item.id}><strong>{item.title}</strong>{item.detail}</li>)}</ul></article></div>}<p className="seo-footer-note">The score is calculated from the checks shown here. It is not a ranking guarantee, Lighthouse score, or security penetration test.</p></section></div></main>;
}
