import Link from "next/link";
import { Header } from "@/components/Header";
import "../tools/seo-audit/seo-audit.css";
import "./portfolio.css";

const studentTools = [
  ["GST Calculator", "/tax-estimator", "Estimate tax with clear year and regime inputs."],
  ["Invoice Generator", "/tools/invoice", "Create a professional GST invoice and save it locally."],
  ["Resume SEO Audit", "/resume-ai", "Review resume structure and extract the next edit."],
  ["Assignment SEO Check", "/tools/seo-audit?mode=assignment", "Check headings, links, and discoverability signals."],
  ["Free SEO Audit Tool", "/tools/seo-audit", "Run a real passive report without an external handoff."],
  ["Website Speed Test", "/tools/seo-audit?mode=speed", "Measure initial public response timing inside the audit."],
];
const officeTools = [
  ["GST Filing Checklist", "/gst", "Keep GST workflow steps visible before submission."],
  ["Tax Calculator FY25-26", "/tax-estimator", "Compare a simple estimate before filing decisions."],
  ["Professional Invoice with GST", "/tools/invoice", "Draft tax-ready invoices for client review."],
  ["Vendor Security Score", "/security-score", "Open the internal passive security workflow."],
  ["SEO Audit Report", "/tools/seo-audit", "Create an evidence-based report with fixes."],
  ["Install GVC OS", "/tools/seo-audit?mode=gvc", "Read the local-first operating workflow."],
];

function PortfolioGroup({ title, items }: { title: string; items: string[][] }) {
  return <section className="portfolio-group"><div className="portfolio-heading"><div className="seo-eyebrow">{title}</div><p>Useful, focused tools with an internal route and a visible next step.</p></div><div className="portfolio-grid">{items.map(([name, href, description], index) => <article className="portfolio-card" key={`${href}-${name}`}><span className="portfolio-index">0{index + 1}</span><h2>{name}</h2><p>{description}</p><Link className="seo-button secondary" href={href}>Use now <span aria-hidden="true">→</span></Link></article>)}</div></section>;
}

export default function PortfolioPage() {
  return <main className="seo-page portfolio-page"><div className="seo-shell"><Header /><section className="portfolio-hero"><div className="seo-eyebrow">DhanSetuHub / giant working portfolio</div><h1>One workspace for <span className="seo-gradient">learning and work.</span></h1><p className="seo-lede">A focused collection of GST, tax, document, and evidence tools for students, offices, and small Indian businesses. Every button stays inside the DhanSetu workflow.</p></section><PortfolioGroup title="For students" items={studentTools} /><PortfolioGroup title="For offices" items={officeTools} /></div></main>;
}
