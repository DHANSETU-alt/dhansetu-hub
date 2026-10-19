"use client";

import Link from "next/link";
import { ArrowRight, BookOpen, Cloud, Download, LockKeyhole, Menu, Sparkles, Wand2, WalletCards, X } from "lucide-react";
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
          <div className="bloom-hero"><span className="bloom-mark bloom-mark-large">d</span><h1>A calmer way forward for <em>money</em> and work.</h1><p>Private browser tools for your money, documents, and next big idea.</p><div className="bloom-hero-actions"><Link className="bloom-cta liquid-glass-strong" href="/smartbudget">Open SmartBudget <span className="icon-orb"><WalletCards size={15} /></span></Link><Link className="bloom-cta bloom-cta-secondary liquid-glass" href="/tools">Try Idea Lab <span className="icon-orb"><Download size={15} /></span></Link></div><div className="bloom-tags"><Link href="/tools" className="liquid-glass service-tag"><Cloud size={14} /><span><strong>Idea Lab</strong><small>Evidence-guided</small></span></Link><Link href="/tools/image-to-pdf" className="liquid-glass service-tag"><LockKeyhole size={14} /><span><strong>Local Docs</strong><small>100% private</small></span></Link><Link href="/smartbudget" className="liquid-glass service-tag"><WalletCards size={14} /><span><strong>SmartBudget</strong><small>Your money</small></span></Link></div></div>
          <footer className="bloom-quote"><small>VISIONARY DESIGN</small><blockquote>“We imagined a realm <em>with no ending.</em>”</blockquote><div className="bloom-author"><i /> MARCUS AURELIO <i /></div></footer>
        </div>
      </section>
      <aside className="bloom-right"><div className="bloom-top-actions"><div className="liquid-glass social-pill"><Link href="/tools" aria-label="Explore tools">Tools</Link><Link href="/smartbudget" aria-label="Open SmartBudget">Budget</Link><Link href="/contact" aria-label="Contact support">Help</Link><ArrowRight size={15} /></div><Link href="/login?next=/billing" className="liquid-glass account-pill"><Sparkles size={15} /> Account</Link></div><Link href="/pricing" className="liquid-glass bloom-community"><Sparkles size={18} /><strong>Choose your next step</strong><p>Free browser tools, or verified lifetime access for SmartBudget.</p><span className="inline-cta">See plans <ArrowRight size={13} /></span></Link><div className="bloom-features liquid-glass-strong"><div className="feature-grid"><Link href="/tools" className="liquid-glass feature-card"><Wand2 size={20} /><strong>Idea Lab</strong><span>Test demand with a transparent, evidence-guided validator</span><span className="inline-cta">Open tool <ArrowRight size={13} /></span></Link><Link href="/smartbudget" className="liquid-glass feature-card"><BookOpen size={20} /><strong>SmartBudget</strong><span>Track income and expenses locally in your browser</span><span className="inline-cta">Open workspace <ArrowRight size={13} /></span></Link></div><Link href="/tools/image-to-pdf" className="liquid-glass feature-bottom"><span className="feature-thumb">✦</span><span><strong>Local Document Tools</strong><small>Combine images locally without uploading documents.</small></span><span className="plus">+</span></Link></div></aside>
    </div>
  </main>;
}
