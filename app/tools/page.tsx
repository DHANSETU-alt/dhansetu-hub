import Link from "next/link";

const tools = [
  ["Image to PDF", "/tools/image-to-pdf", "Combine images into a PDF locally in your browser."],
  ["Invoice Generator", "/tools/invoice", "Create a simple invoice from the existing tool desk."],
  ["PDF Studio", "/pdf-studio", "Private document workflows in the Dhansetu suite."],
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

  return <main className="min-h-screen bg-slate-950 px-6 py-16 text-white"><section className="mx-auto max-w-5xl"><p className="text-sm font-bold uppercase tracking-[0.2em] text-emerald-400">Dhansetu Tools</p><h1 className="mt-4 text-5xl font-black">Useful tools for everyday work.</h1><p className="mt-5 max-w-2xl text-slate-300">Privacy-first utilities that make common document and business tasks simpler.</p><section className="mt-10 rounded-3xl border border-emerald-400/30 bg-slate-900 p-7"><p className="text-xs font-bold uppercase tracking-[.2em] text-emerald-400">AI Idea Validator</p><h2 className="mt-3 text-2xl font-bold">Test demand before spending 30 days building.</h2><form className="mt-5 flex flex-col gap-3 sm:flex-row" action="/tools"><input name="idea" defaultValue={result?.idea ?? ""} required placeholder="Describe your AI service idea" className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 py-3" /><button className="rounded-xl bg-emerald-500 px-6 py-3 font-bold text-slate-950">Validate idea</button></form>{result && <div className="mt-6 grid gap-4 rounded-2xl border border-slate-700 bg-slate-950 p-5 sm:grid-cols-[1fr_auto] sm:items-center"><div><p className="text-sm text-slate-400">Result for “{result.idea}”</p><p className="mt-1 text-xl font-bold">{result.verdict}</p><p className="mt-2 text-sm text-slate-400">Next step: interview five target customers and ask for a paid pilot before building integrations.</p></div><div className="text-left sm:text-right"><p className="text-4xl font-black text-emerald-400">{result.score}/100</p><p className="text-xs uppercase tracking-wider text-slate-500">validation signal</p></div></div>}</section><div className="mt-10 grid gap-5 md:grid-cols-3">{tools.map(([name, href, description]) => <article key={href} className="rounded-2xl border border-slate-700 bg-slate-900 p-6"><h2 className="text-xl font-bold">{name}</h2><p className="mt-3 min-h-16 text-sm text-slate-400">{description}</p><Link className="mt-5 inline-block rounded-xl bg-emerald-500 px-4 py-2 font-bold text-slate-950" href={href}>Open tool</Link></article>)}</div></section></main>;
}
