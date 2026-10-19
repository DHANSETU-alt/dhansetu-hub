import Link from "next/link";
import "../service.css";

const tools = [
  ["Image to PDF", "/tools/image-to-pdf", "Combine images locally. Nothing is uploaded.", "Local · no account"],
  ["GST Invoice Generator", "/tools/invoice", "Create a GST-ready invoice and save it as a PDF.", "Local · print to PDF"],
  ["Tax Estimator", "/tax-estimator", "Estimate salaried tax with explicit year and regime inputs.", "Local · estimate only"],
  ["GST LeakShield", "/gst", "Compare purchase-register and GSTR-2B CSV exports locally.", "Local · review only"],
  ["SmartBudget", "/smartbudget", "Track income, expenses, and leak checks in this browser.", "Local-first workspace"],
] as const;

function validateIdea(rawIdea: string) {
  const idea = rawIdea.trim();
  const words = idea.split(/\s+/).filter(Boolean);
  const signals = ["customer", "pay", "problem", "save", "business", "india", "ai", "agency"];
  const signalCount = signals.filter((signal) => idea.toLowerCase().includes(signal)).length;
  const score = Math.min(94, Math.max(22, 35 + Math.min(words.length, 12) * 3 + signalCount * 6));
  const verdict = score >= 70 ? "Strong test candidate" : score >= 50 ? "Refine before building" : "Needs sharper customer evidence";
  return { idea, score, verdict };
}

export default async function ToolsPage({
  searchParams,
}: {
  searchParams?: Promise<{ idea?: string }>;
}) {
  const params = searchParams ? await searchParams : {};
  const result = params.idea ? validateIdea(params.idea) : null;

  return <main className="service-page"><section className="service-shell"><nav className="service-nav"><Link className="service-brand" href="/">d<span>hansetu</span></Link><Link className="service-back" href="/">Back to home</Link></nav><p className="service-kicker">Dhansetu tools</p><h1>Choose a task.<br />Get a useful result.</h1><p className="service-lead">Privacy-first tools for documents, money, tax, and early product decisions. Start without an account where the work can stay in your browser.</p><section className="service-panel"><p className="service-kicker">Idea Lab · evidence-guided</p><h2>Pressure-test an idea before spending 30 days building.</h2><p className="service-muted mt-3">This is a structured heuristic, not an AI-generated market report. It gives you a starting signal and a concrete customer interview next step.</p><form className="mt-5 flex flex-col gap-3 sm:flex-row" action="/tools"><input name="idea" defaultValue={result?.idea ?? ""} required placeholder="Describe the customer, problem, and paid outcome" className="flex-1 rounded-xl border px-4 py-3" /><button className="service-button">Assess idea</button></form>{result && <div className="service-card mt-6"><p className="service-muted">Assessment for “{result.idea}”</p><p className="mt-1 text-xl font-bold">{result.verdict} · {result.score}/100</p><p className="service-muted mt-2">Next step: interview five target customers and ask for a paid pilot.</p></div>}</section><div className="service-grid">{tools.map(([name, href, description, mode]) => <article key={href} className="service-card"><p className="inline-flex w-max rounded-full bg-emerald-50 px-2.5 py-1 text-[.68rem] font-bold uppercase tracking-wide text-emerald-700">{mode}</p><h2 className="mt-4 text-2xl">{name}</h2><p className="service-muted mt-3 min-h-16 text-sm">{description}</p><Link className="service-button mt-5 inline-block" href={href}>Open {name} →</Link></article>)}</div></section></main>;
}
