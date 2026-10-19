'use client';

import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-black text-white">
      <nav className="fixed top-0 left-0 right-0 z-50 h-[70px] flex items-center px-12 bg-black/80 backdrop-blur border-b border-emerald-500/10">
        <a href="/" className="text-2xl font-bold bg-gradient-to-r from-emerald-400 to-emerald-300 bg-clip-text text-transparent">
          Dhansetu Hub
        </a>
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex gap-12 hidden lg:flex">
          <a href="#features" className="text-sm font-medium text-white/70 hover:text-emerald-400 transition">Features</a>
          <a href="#pricing" className="text-sm font-medium text-white/70 hover:text-emerald-400 transition">Pricing</a>
          <a href="/tools" className="text-sm font-medium text-white/70 hover:text-emerald-400 transition">Tools</a>
        </div>
        <div className="ml-auto flex gap-3 hidden lg:flex">
          <Link href="/checkout?tier=founding_lifetime" className="px-5 py-2 text-sm font-semibold rounded-lg bg-emerald-500 text-black hover:bg-emerald-400 transition">
            Get Started →
          </Link>
        </div>
      </nav>

      <section className="pt-[70px] min-h-screen flex flex-col items-center justify-center px-6 py-20 bg-gradient-to-b from-slate-900 via-black to-black relative overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-1/3 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl"></div>
          <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl"></div>
        </div>

        <div className="text-center">
          <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-white via-emerald-300 to-emerald-400 bg-clip-text text-transparent leading-tight">
            Build wealth<br />confidently.
          </h1>
          <p className="text-lg md:text-xl text-white/60 mb-8 max-w-2xl mx-auto leading-relaxed">
            SmartBudget, Resume AI, PDF Studio, and PeopleDesk.<br />
            Privacy-first tools for Indian professionals.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/checkout?tier=founding_lifetime" className="px-8 py-4 bg-emerald-500 text-black font-semibold rounded-xl hover:bg-emerald-400 transition transform hover:-translate-y-1 inline-block">
              Get Lifetime Access ₹1,999 →
            </Link>
            <Link href="/tools/image-to-pdf" className="px-8 py-4 bg-white/5 border border-emerald-500/30 text-white font-semibold rounded-xl hover:bg-emerald-500/10 transition transform hover:-translate-y-1 inline-block">
              Try Free Tools →
            </Link>
          </div>
        </div>
      </section>

      <section id="features" className="py-20 px-6 bg-black">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            { name: 'SmartBudget', desc: 'Track expenses, build budgets, grow wealth with AI.' },
            { name: 'Resume AI', desc: 'Create pro resumes instantly. Get noticed by recruiters.' },
            { name: 'PDF Studio', desc: 'Convert images to PDF locally. Complete privacy.' },
            { name: 'PeopleDesk', desc: 'Support ticketing for your team. Professional.' },
          ].map((feature, i) => (
            <div key={i} className="p-6 rounded-xl bg-white/5 border border-emerald-500/20 hover:border-emerald-500/50 hover:bg-emerald-500/5 transition transform hover:-translate-y-2">
              <h3 className="text-lg font-bold text-emerald-400 mb-2">{feature.name}</h3>
              <p className="text-sm text-white/60">{feature.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="pricing" className="py-20 px-6 bg-gradient-to-b from-black to-slate-900">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold text-center mb-16">Simple Pricing</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { tier: 'Starter', price: '₹1,999', features: ['All core tools', 'Updates forever', 'Email support'], id: 'founding_lifetime' },
              { tier: 'Professional', price: '₹9,999', features: ['Everything in Starter', 'Priority support', 'Team features'], id: 'pro_lifetime' },
              { tier: 'Agency', price: '₹19,999', features: ['Everything in Pro', 'Dedicated support', 'White-label'], id: 'team_lifetime' },
            ].map((plan) => (
              <div key={plan.id} className="p-8 rounded-xl border-2 border-emerald-500/30 hover:border-emerald-500 hover:bg-emerald-500/5 transition transform hover:scale-105">
                <h3 className="text-xl font-bold mb-2">{plan.tier}</h3>
                <div className="text-4xl font-bold text-emerald-400 mb-2">{plan.price}</div>
                <p className="text-sm text-white/50 mb-6">One payment. Lifetime access.</p>
                <ul className="space-y-3 mb-8">
                  {plan.features.map((f, i) => <li key={i} className="text-sm text-white/70">✓ {f}</li>)}
                </ul>
                <Link href={`/checkout?tier=${plan.id}`} className="w-full block py-3 bg-emerald-500 text-black font-semibold rounded-lg hover:bg-emerald-400 transition text-center">
                  Get Started
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
