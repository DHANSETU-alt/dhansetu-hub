import Link from "next/link";
import { PDF_TOOLS } from "./tools";

export default function PdfToolsPage() {
  return (
    <main className="min-h-screen bg-[#0a1410] px-5 py-10 text-white sm:px-8">
      <section className="mx-auto max-w-7xl">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-emerald-200/10 pb-8">
          <Link href="/" className="flex items-center gap-3 text-lg font-bold tracking-tight">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-emerald-300 text-[#0a1410]">DS</span>
            <span>DhanSetu <span className="text-emerald-300">PDF Tools</span></span>
          </Link>
          <Link href="/portfolio" className="text-sm text-emerald-200 hover:text-white">Portfolio</Link>
        </header>
        <div className="max-w-3xl py-14">
          <p className="text-xs font-bold uppercase tracking-[0.24em] text-emerald-300">Local document workspace</p>
          <h1 className="mt-4 text-4xl font-black tracking-tight sm:text-6xl">26 PDF workflows.<br /><span className="text-emerald-300">Private by default.</span></h1>
          <p className="mt-6 text-lg leading-8 text-emerald-50/65">Original DhanSetu tooling for operators, students, and offices. The implemented browser tools process files locally; planned workers stay visibly marked until they are verified.</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PDF_TOOLS.map((tool, index) => (
            <Link key={tool.slug} href={`/pdf-tools/${tool.slug}`} className="group rounded-2xl border border-emerald-100/10 bg-white/[0.04] p-5 transition hover:border-emerald-300/50 hover:bg-emerald-300/[0.08]">
              <div className="flex items-center justify-between text-xs text-emerald-200/55"><span>0{index + 1}</span><span className={tool.implemented ? "text-emerald-300" : "text-amber-300"}>{tool.implemented ? "LOCAL NOW" : "WORKER NEXT"}</span></div>
              <h2 className="mt-8 text-lg font-bold group-hover:text-emerald-200">{tool.name}</h2>
              <p className="mt-2 min-h-12 text-sm leading-6 text-emerald-50/55">{tool.description}</p>
              <span className="mt-5 inline-block text-sm font-semibold text-emerald-300">Open workflow →</span>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
