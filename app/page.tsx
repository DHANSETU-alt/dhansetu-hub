"use client";

import Link from "next/link";
import { ArrowRight, BookOpen, Download, Menu, Sparkles, Wand2, X } from "lucide-react";
import { useState } from "react";
import "./home.css";

const video = "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260315_073750_51473149-4350-4920-ae24-c8214286f323.mp4";

export default function Home() {
  const [open, setOpen] = useState(false);
  return <main className="bloom-page">
    <video className="bloom-video" autoPlay muted loop playsInline aria-hidden="true"><source src={video} type="video/mp4" /></video>
    <div className="bloom-wash" />
    <div className="bloom-shell">
      <section className="bloom-left">
        <div className="bloom-panel bloom-panel-strong" />
        <div className="bloom-content">
          <header className="bloom-nav"><Link href="/" className="bloom-brand"><span className="bloom-logo">d</span><span>dhansetu</span></Link><button className="glass-pill menu-button" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? <X size={16} /> : <Menu size={16} />} <span>Menu</span></button></header>
          {open && <nav className="bloom-mobile-menu liquid-glass-strong"><Link href="/tools">Workspace</Link><Link href="/smartbudget">SmartBudget</Link><Link href="/contact">Contact</Link><Link href="/login">Sign in</Link></nav>}
          <div className="bloom-hero"><span className="bloom-mark bloom-mark-large">d</span><h1>Innovating the <em>spirit</em> of <span>bloom</span> AI</h1><p>Clarity for your money, momentum for your next idea.</p><Link className="bloom-cta liquid-glass-strong" href="/tools">Explore Now <span className="icon-orb"><Download size={15} /></span></Link><div className="bloom-tags"><span className="liquid-glass">Artistic Gallery</span><span className="liquid-glass">AI Generation</span><span className="liquid-glass">3D Structures</span></div></div>
          <footer className="bloom-quote"><small>VISIONARY DESIGN</small><blockquote>“We imagined a realm <em>with no ending.</em>”</blockquote><div className="bloom-author"><i /> MARCUS AURELIO <i /></div></footer>
        </div>
      </section>
      <aside className="bloom-right"><div className="bloom-top-actions"><div className="liquid-glass social-pill"><a href="https://twitter.com" aria-label="Twitter">𝕏</a><a href="https://linkedin.com" aria-label="LinkedIn">in</a><a href="https://instagram.com" aria-label="Instagram">◎</a><ArrowRight size={15} /></div><Link href="/login" className="liquid-glass account-pill"><Sparkles size={15} /> Account</Link></div><div className="liquid-glass bloom-community"><Sparkles size={18} /><strong>Enter our ecosystem</strong><p>Tools that turn everyday decisions into beautiful progress.</p></div><div className="bloom-features liquid-glass-strong"><div className="feature-grid"><div className="liquid-glass feature-card"><Wand2 size={20} /><strong>Processing</strong><span>Ideas into useful steps</span></div><div className="liquid-glass feature-card"><BookOpen size={20} /><strong>Growth Archive</strong><span>Your progress, remembered</span></div></div><Link href="/tools/image-to-pdf" className="liquid-glass feature-bottom"><span className="feature-thumb">✦</span><span><strong>Advanced Plant Sculpting</strong><small>Shape a clearer future with focused tools.</small></span><span className="plus">+</span></Link></div></aside>
    </div>
  </main>;
}
