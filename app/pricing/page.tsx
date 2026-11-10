import Link from "next/link";
import { PUBLIC_PLANS } from "@/lib/payment/tiers";

const descriptions: Record<keyof typeof PUBLIC_PLANS, string> = {
  free: "Idea Lab, local document tools, and SmartBudget in your browser.",
  smartbudget_pro: "Personal money workspace with server-verified account access.",
  all_access: "SmartBudget plus the complete DhanSetu tools workspace.",
  founder_pass: "Lifetime access to the All Access and SmartBudget Pro workspaces. Limited to 100 verified purchases.",
};

export default function PricingPage() {
  return (
    <main className="service-page">
      <section className="service-shell">
        <nav className="service-nav">
          <Link className="service-brand" href="/">d<span>hansetu</span></Link>
          <Link className="service-back" href="/tools">Explore tools</Link>
        </nav>
        <p className="service-kicker">Simple access</p>
        <h1>Choose the workspace<br />that fits your next step.</h1>
        <p className="service-lead">Start with browser-based tools, or unlock the money workspace with one verified Razorpay payment.</p>
        <div className="service-grid">
          {Object.entries(PUBLIC_PLANS).map(([id, plan]) => {
            const tier = id as keyof typeof PUBLIC_PLANS;
            const free = tier === "free";
            return (
              <article className={`service-card ${tier === "all_access" ? "pricing-popular" : ""}`} key={id}>
                {tier === "all_access" && <p className="service-kicker">Most popular</p>}
                <p className="service-kicker">{free ? "Start here" : "Lifetime access"}</p>
                <h2 className="text-2xl">{plan.label}</h2>
                <p className="mt-3 text-3xl font-bold">{free ? "Free" : `₹${plan.amountPaise / 100}`}</p>
                <p className="service-muted mt-3">{descriptions[tier]}</p>
                <Link className="service-button mt-5 inline-block" href={free ? "/tools" : `/checkout?tier=${id}`}>
                  {free ? "Start Free Workspace →" : `Get ${plan.label} - ₹${plan.amountPaise / 100} →`}
                </Link>
              </article>
            );
          })}
        </div>
      </section>
    </main>
  );
}
