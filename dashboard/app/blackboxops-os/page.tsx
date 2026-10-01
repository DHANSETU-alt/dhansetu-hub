"use client";

import Link from "next/link";
import { ArrowUpRight, Menu, ShieldCheck, Sparkles, WalletCards } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

const PRODUCTS = [
  ["Budget & money leaks", "See what arrived, what is committed, and what is safe to spend next.", "/blackboxops-os/portal"],
  ["Tax & GST clarity", "Evidence-led estimates and review queues—not unexplained AI arithmetic.", "/dhansetu-ai"],
  ["Career tools", "Turn an existing resume into a clearer, editable application workflow.", "/pdf-studio"],
  ["Partners", "A reviewed network for software affiliates and qualified service providers.", "/blackboxops-os/onboarding"],
];
const COINS = Array.from({ length: 28 }, (_, index) => ({ left: `${(index * 37) % 101}%`, delay: `${(index % 9) * 0.7}s`, duration: `${8 + (index % 6)}s`, size: `${12 + (index % 4) * 3}px` }));

export default function DhanSetuHomePage() {
  const [spotlight, setSpotlight] = useState({ x: -999, y: -999 });
  const raw = useRef({ x: -999, y: -999 });
  const smooth = useRef({ x: -999, y: -999 });
  const raf = useRef<number | null>(null);
  useEffect(() => {
    const move = (event: MouseEvent) => { raw.current = { x: event.clientX, y: event.clientY }; };
    const tick = () => { smooth.current.x += (raw.current.x - smooth.current.x) * 0.1; smooth.current.y += (raw.current.y - smooth.current.y) * 0.1; setSpotlight({ x: smooth.current.x, y: smooth.current.y }); raf.current = requestAnimationFrame(tick); };
    window.addEventListener("mousemove", move); raf.current = requestAnimationFrame(tick);
    return () => { window.removeEventListener("mousemove", move); if (raf.current) cancelAnimationFrame(raf.current); };
  }, []);
  const coins = useMemo(() => COINS, []);
  return (
    <main className="dhansetu-landing min-h-screen bg-[#071311] text-[#eef8f2]">
      <nav className="fixed left-0 right-0 top-0 z-[100] flex items-center justify-between p-4 sm:p-5" aria-label="Main navigation">
        <Link href="/blackboxops-os" className="flex items-center gap-2 text-white" aria-label="DhanSetu home"><span className="grid h-7 w-7 place-items-center rounded-lg bg-[#79e2a2] text-[#071311]"><WalletCards size={17} /></span><span className="font-playfair text-2xl italic">DhanSetu</span></Link>
        <div className="hidden items-center gap-1 rounded-full border border-white/20 bg-white/10 px-2 py-2 backdrop-blur-md md:flex">{["Overview", "Money leaks", "Tax & GST", "Career", "Partners"].map((item, index) => <a key={item} href={index === 0 ? "#top" : "#products"} className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors hover:bg-white/20 hover:text-white ${index === 0 ? "bg-white text-gray-900" : "text-white/80"}`}>{item}</a>)}</div>
        <div className="flex items-center gap-3"><Link href="/blackboxops-os/portal" className="hidden rounded-full bg-white px-6 py-2.5 text-sm font-semibold text-gray-900 hover:bg-gray-100 md:block">Open workspace</Link><Link href="/blackboxops-os/portal" className="rounded-full border border-white/30 p-2 text-white md:hidden" aria-label="Open workspace"><Menu size={18} /></Link></div>
      </nav>
      <section id="top" className="relative min-h-screen w-full overflow-hidden bg-[#071311]" style={{ minHeight: "100dvh" }}>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_20%,rgba(65,190,122,.18),transparent_35%),linear-gradient(135deg,#071311_0%,#0b2119_48%,#03100d_100%)]" />
        <div className="coin-rain" aria-hidden="true">{coins.map((coin, index) => <span key={index} style={{ left: coin.left, animationDelay: coin.delay, animationDuration: coin.duration, width: coin.size, height: coin.size }}><span>₹</span></span>)}</div>
        <div className="dhansetu-spotlight" style={{ left: spotlight.x, top: spotlight.y }} aria-hidden="true" />
        <div className="relative z-10 mx-auto flex min-h-screen max-w-7xl flex-col justify-between px-5 pb-10 pt-28 sm:px-10 sm:pb-14 sm:pt-32" style={{ minHeight: "100dvh" }}>
          <div className="pointer-events-none mx-auto max-w-5xl text-center"><p className="hero-anim hero-fade mb-5 text-xs font-semibold uppercase tracking-[0.24em] text-[#79e2a2]">A calmer money operating system</p><h1 className="text-white leading-[0.94]"><span className="hero-anim hero-reveal block font-playfair text-5xl font-normal italic sm:text-7xl md:text-8xl">Make money feel</span><span className="hero-anim hero-reveal mt-1 block text-5xl font-normal tracking-[-0.08em] sm:text-7xl md:text-8xl">less complicated.</span></h1><p className="hero-anim hero-fade mx-auto mt-7 max-w-2xl text-base leading-7 text-white/75 sm:text-lg">Budget smarter, spot money leaks, understand tax documents, and make your next financial decision with evidence—not guesswork.</p><div className="pointer-events-auto mt-8 flex flex-col justify-center gap-3 sm:flex-row"><Link href="/blackboxops-os/portal" className="rounded-full bg-[#e8ad56] px-7 py-3 text-sm font-semibold text-[#1b1308] transition-all hover:scale-[1.03] hover:bg-[#f2bf6d] hover:shadow-lg hover:shadow-[#e8ad56]/30">Start with SmartBudget <ArrowUpRight className="ml-1 inline" size={16} /></Link><Link href="/blackboxops-os/pricing" className="rounded-full border border-white/25 px-7 py-3 text-sm font-medium text-white transition hover:border-white/60 hover:bg-white/10">See simple pricing</Link></div></div>
          <div className="grid gap-6 sm:grid-cols-[1fr_auto] sm:items-end"><div className="hero-anim hero-fade hidden max-w-[280px] sm:block"><p className="text-sm leading-relaxed text-white/75">Your salary, subscriptions, bills, tax documents, and goals—connected into one clear view of what your money can do next.</p><div className="mt-5 flex items-center gap-2 text-xs text-[#b9f6cf]"><ShieldCheck size={15} /> Privacy-first by design</div></div><div className="hero-anim hero-fade max-w-full sm:max-w-[300px]"><p className="text-xs leading-relaxed text-white/70 sm:text-sm">Every figure is labelled actual, estimated, pending, or unavailable. No invented balances. No hidden assumptions.</p><Link href="#products" className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-[#e8ad56]">Explore your money paths <ArrowUpRight size={16} /></Link></div></div>
        </div>
      </section>
      <section id="products" className="relative z-10 border-t border-white/10 bg-[#071311] px-5 py-20 sm:px-10 md:py-28"><div className="mx-auto max-w-7xl"><div className="max-w-2xl"><p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#79e2a2]">One bridge, four clear paths</p><h2 className="mt-4 text-3xl font-semibold tracking-tight sm:text-5xl">Useful tools for decisions that matter.</h2></div><div className="mt-10 grid gap-4 sm:grid-cols-2">{PRODUCTS.map(([title, text, href]) => <Link key={title} href={href} className="group rounded-3xl border border-white/10 bg-white/[0.035] p-6 transition hover:-translate-y-1 hover:border-[#79e2a2]/50 hover:bg-white/[0.06]"><Sparkles className="text-[#e8ad56]" size={18} /><h3 className="mt-5 text-xl font-semibold group-hover:text-[#c9f8d8]">{title}</h3><p className="mt-3 leading-7 text-[#9eb3a7]">{text}</p><span className="mt-6 inline-block text-sm font-semibold text-[#79e2a2]">Explore path →</span></Link>)}</div></div></section>
      <footer className="border-t border-white/10 bg-[#071311] px-5 py-8 text-xs text-[#80978b] sm:px-10"><div className="mx-auto flex max-w-7xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><span>© 2026 DhanSetu Hub · dhansetuhub.in</span><div className="flex gap-5"><Link href="/privacy">Privacy</Link><Link href="/terms">Terms</Link><Link href="/refund">Refunds</Link></div></div></footer>
    </main>
  );
}
