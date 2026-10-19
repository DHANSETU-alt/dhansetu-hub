import type { Metadata } from "next";
import { PartnerApplicationForm } from "@/components/partners/PartnerApplicationForm";

export const metadata: Metadata = {
  title: "Partner with DhanSetu — Refer, advise, or build with us",
  description:
    "Apply as a software affiliate, a qualified tax, GST or career professional, or a licensed partner. Every application is reviewed by a person before anything goes live.",
};

const tracks = [
  {
    eyebrow: "For creators and consultants",
    title: "Software affiliate",
    body: "You already advise people about their money or their career. Share DhanSetu with a tracked link and earn on the purchases it leads to.",
    points: [
      "A unique link, with the introduction credited to you",
      "Attribution is first touch, so a later link cannot take your credit",
      "Earnings arise only from a payment that has actually settled",
    ],
  },
  {
    eyebrow: "For CAs and practitioners",
    title: "Qualified professional",
    body: "Tax, GST and career professionals who want reviewed work sent to them. Your credentials are checked by a person before your profile exists.",
    points: [
      "Tax, GST and career tracks are reviewed separately",
      "No profile is published until review is complete",
      "You decide which work you take",
    ],
  },
  {
    eyebrow: "For licensed channels",
    title: "Regulated partner",
    body: "Insurance and other regulated activity is not switched on by an application. It needs the right licence and a signed agreement, and we will say so plainly.",
    points: [
      "Licence evidence required before anything is enabled",
      "A signed agreement, not a checkbox",
      "Customers always see the commercial relationship disclosed",
    ],
  },
];

const steps = [
  { n: "01", t: "Apply", d: "The form below. A few minutes, and it asks what you actually do." },
  { n: "02", t: "A person reads it", d: "Nothing is automated. Applications start as pending review and stay there until a human decides." },
  { n: "03", t: "Terms in writing", d: "If it is a fit, you get the commercial terms in writing before you promote anything." },
  { n: "04", t: "You are credited", d: "Your link attributes the introduction. Commission is calculated only on a settled payment, and reversed if it is refunded." },
];

export default function PartnersPage() {
  return (
    <main className="bg-white text-[color:var(--ink)]">
      <section className="relative overflow-hidden border-b border-[color:var(--line)]">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_60%_at_20%_0%,#ecfdf5_0%,transparent_60%)]"
        />
        <div className="relative mx-auto max-w-5xl px-5 py-16 sm:px-8 sm:py-24">
          <p className="ds-rise text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--accent)]">
            DhanSetu partner network
          </p>
          <h1 className="ds-rise mt-4 max-w-3xl text-4xl font-bold leading-[1.08] text-balance sm:text-6xl">
            Good advice travels through people, not ads.
          </h1>
          <p className="ds-rise mt-6 max-w-2xl text-lg leading-relaxed text-[color:var(--ink-soft)]">
            DhanSetu helps salaried people and small businesses see their money clearly. If you
            already have their trust, there is a straightforward way to work together — and to be
            paid for the introductions that turn into real customers.
          </p>
          <div className="ds-rise mt-8 flex flex-wrap gap-3">
            <a
              href="#apply"
              className="rounded-full bg-[color:var(--ink)] px-6 py-3 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-[color:var(--accent)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--accent)]"
            >
              Apply to join
            </a>
            <a
              href="#how"
              className="rounded-full border border-[color:var(--line)] px-6 py-3 text-sm font-semibold transition hover:border-[color:var(--ink)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--accent)]"
            >
              How it works
            </a>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-5 py-16 sm:px-8">
        <h2 className="text-2xl font-bold sm:text-3xl">Three ways to work with us</h2>
        <p className="mt-3 max-w-2xl text-[color:var(--ink-soft)]">
          Pick the one that matches what you actually do. You can move between them later.
        </p>
        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {tracks.map((track) => (
            <article
              key={track.title}
              className="flex flex-col rounded-2xl border border-[color:var(--line)] bg-[color:var(--surface)] p-6 transition hover:-translate-y-1 hover:border-[color:var(--accent)]"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[color:var(--accent)]">
                {track.eyebrow}
              </p>
              <h3 className="mt-3 text-xl font-semibold">{track.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-[color:var(--ink-soft)]">{track.body}</p>
              <ul className="mt-5 space-y-2 text-sm text-[color:var(--ink-soft)]">
                {track.points.map((point) => (
                  <li key={point} className="flex gap-2">
                    <span aria-hidden="true" className="mt-2 h-1 w-1 flex-none rounded-full bg-[color:var(--accent)]" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section id="how" className="border-y border-[color:var(--line)] bg-[color:var(--surface-sunk)]">
        <div className="mx-auto max-w-5xl px-5 py-16 sm:px-8">
          <h2 className="text-2xl font-bold sm:text-3xl">How joining works</h2>
          <ol className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {steps.map((step) => (
              <li key={step.n}>
                <span className="tabular text-sm font-semibold text-[color:var(--accent)]">{step.n}</span>
                <h3 className="mt-2 text-lg font-semibold">{step.t}</h3>
                <p className="mt-2 text-sm leading-relaxed text-[color:var(--ink-soft)]">{step.d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-5 py-16 sm:px-8">
        <h2 className="text-2xl font-bold sm:text-3xl">Before you apply, the honest part</h2>
        <div className="mt-6 space-y-4 text-[color:var(--ink-soft)]">
          <p>
            DhanSetu is early. Traffic is small and the partner network is new, so nobody here is
            going to promise you volume. If you need guaranteed monthly earnings today, this is not
            that. If you want to be early in something built carefully, apply.
          </p>
          <p>
            Commission rates are agreed in writing with you rather than advertised on this page, and
            nothing is paid on a transaction that has not settled. A refunded purchase reverses the
            commission — we would rather tell you that now than surprise you later.
          </p>
          <p>
            There is no joining fee, no deposit, and nothing to buy. Any programme that charges you
            to start earning is selling you the programme.
          </p>
        </div>
      </section>

      <section id="apply" className="border-t border-[color:var(--line)] bg-[color:var(--surface-sunk)]">
        <div className="mx-auto max-w-2xl px-5 py-16 sm:px-8">
          <h2 className="text-2xl font-bold sm:text-3xl">Apply to join</h2>
          <p className="mt-3 text-[color:var(--ink-soft)]">
            We read every application. Please do not send passwords, client data, or anything covered
            by someone else&rsquo;s confidentiality agreement.
          </p>
          <div className="mt-8">
            <PartnerApplicationForm />
          </div>
        </div>
      </section>
    </main>
  );
}
