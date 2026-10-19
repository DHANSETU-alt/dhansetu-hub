"use client";
import Link from "next/link";
import { useEffect } from "react";
import "./home.css";

const wideVideo = "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260826_125226_45cb4f38-aa7e-47e1-885d-ae0b69745369.mp4";
const narrowVideo = "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260826_125242_daae1570-386d-4bd5-8896-80499e2371e0.mp4";
const services = [
  { name: "SmartBudget", category: "Money workspace", badge: "LOCAL", description: "Your money stays in your browser", href: "/smartbudget", tone: "service-card--rose", cta: "Open SmartBudget" },
  { name: "Image to PDF", category: "Document tool", badge: "PRIVATE", description: "Convert images to PDF offline", href: "/tools/image-to-pdf", tone: "service-card--blue", cta: "Open Image to PDF" },
  { name: "GST Invoice Generator", category: "Business document", badge: "PRIVATE", description: "Create GST invoices instantly", href: "/tools/invoice", tone: "service-card--green", cta: "Open Invoice Generator" },
  { name: "Tax Estimator", category: "Tax planning", badge: "LOCAL", description: "Estimate your tax liability", href: "/tax-estimator", tone: "service-card--violet", cta: "Open Tax Estimator" },
  { name: "GST LeakShield", category: "GST review", badge: "SECURE", description: "Find GST leakage in seconds", href: "/gst", tone: "service-card--orange", cta: "Open LeakShield" },
] as const;

export default function Home() {
  useEffect(() => { const root = document.documentElement; root.classList.add("entrance-active"); const timer = window.setTimeout(() => root.classList.remove("entrance-active"), 3200); if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) root.classList.remove("entrance-active"); return () => { window.clearTimeout(timer); root.classList.remove("entrance-active"); }; }, []);
  return <main className="stage"><video className="stage-motion stage-motion--wide" autoPlay muted loop playsInline preload="auto" aria-hidden="true" poster="https://d2ol7oe51mr4n9.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/5c3ec08f-2dbf-4c0a-8588-f6106a789443.webp"><source src={wideVideo} type="video/mp4" /></video><video className="stage-motion stage-motion--narrow" autoPlay muted loop playsInline preload="none" aria-hidden="true" poster="https://d2ol7oe51mr4n9.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/0f4926a4-e660-4df2-9195-2bfb3e341bdd.webp"><source src={narrowVideo} type="video/mp4" /></video><header className="masthead"><div><h1 className="headline"><span className="headline__line">Your private <span className="dot-word">workspace</span></span><span className="headline__line">for everyday decisions</span></h1><p className="intro">Money, documents, tax, and GST tools in one calm place—<br className="desktop-break" />with clear service boundaries and direct actions<br className="desktop-break" />for your next step.</p></div><nav className="stage-nav" aria-label="Primary"><Link href="/tools">Tools</Link><Link href="/pricing">Plans</Link><Link href="/contact">Contact</Link><Link href="/login">Sign in</Link></nav></header><section className="service-grid-home" aria-label="Dhansetu services">{services.map((service) => <article className={`service-card-home ${service.tone}`} data-testid="service-card" key={service.href}><p className="service-card__category">{service.category}</p><p className="service-card__badge">{service.badge}</p><h2>{service.name}</h2><p className="service-card__description">{service.description}</p><Link className="service-card__cta" href={service.href}>{service.cta}</Link></article>)}</section></main>;
}
