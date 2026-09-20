import Link from "next/link";

const tools = [["Image to PDF", "/tools/image-to-pdf", "Combine images into a PDF locally in your browser."], ["Invoice Generator", "/tools/invoice", "Create a simple invoice from the existing tool desk."], ["PDF Studio", "/pdf-studio", "Private document workflows in the Dhansetu suite."]];

export default function ToolsPage() {
  return <main className="min-h-screen bg-slate-950 px-6 py-16 text-white"><section className="mx-auto max-w-5xl"><p className="text-sm font-bold uppercase tracking-[0.22em] text-emerald-400">Dhansetu Tools</p><h1 className="mt-4 text-5xl font-black">Useful tools for everyday work.</h1><p className="mt-5 max-w-2xl text-slate-300">Privacy-first utilities that make common document and business tasks simpler.</p><div className="mt-10 grid gap-5 md:grid-cols-3">{tools.map(([name, href, description]) => <article key={href} className="rounded-2xl border border-slate-700 bg-slate-900 p-6"><h2 className="text-xl font-bold">{name}</h2><p className="mt-3 min-h-16 text-sm text-slate-400">{description}</p><Link className="mt-5 inline-block rounded-xl bg-emerald-500 px-4 py-2 font-bold text-slate-950" href={href}>Open tool</Link></article>)}</div></section></main>;
}
