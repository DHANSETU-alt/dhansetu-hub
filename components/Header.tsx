"use client";

import Link from "next/link";
import { useState } from "react";

export function Header({ compact = false }: { compact?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <header className={`studio-header${compact ? " studio-header-compact" : ""}`}>
      <Link className="studio-logo" href="/" aria-label="DhanSetu Hub home" onClick={() => setOpen(false)}>
        <span className="studio-logo-mark" aria-hidden="true">⌁</span>
        <span><strong>DhanSetu</strong><small>HUB / LOCAL WORKSPACE</small></span>
      </Link>
      <nav id="studio-navigation" className={`studio-nav${open ? " studio-nav-open" : ""}`} aria-label="Primary navigation">
        <Link href="/gst" onClick={() => setOpen(false)}>GST &amp; Tax</Link>
        <Link href="/tools/seo-audit" onClick={() => setOpen(false)}>SEO audit</Link>
        <Link href="/portfolio" onClick={() => setOpen(false)}>Portfolio</Link>
        <Link href="/tools" onClick={() => setOpen(false)}>Tools</Link>
      </nav>
      <Link className="studio-cta" href="/tools/seo-audit" onClick={() => setOpen(false)}>Run an audit <span aria-hidden="true">→</span></Link>
      <button className="studio-menu" type="button" aria-expanded={open} aria-controls="studio-navigation" onClick={() => setOpen((value) => !value)}>
        <span aria-hidden="true">{open ? "×" : "☰"}</span><span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
      </button>
    </header>
  );
}
