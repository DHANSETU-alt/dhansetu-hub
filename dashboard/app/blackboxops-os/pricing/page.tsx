"use client";

import { useState } from "react";
import Link from "next/link";
import Script from "next/script";
import { SUPPORT_EMAIL } from "@/lib/brand";

// Razorpay's own Checkout.js -- loaded once, opens the real payment modal
// directly on this page. This is the actual fix for the founder's real,
// repeated complaint about the old flow below: that one calls /subscribe,
// which only ever produced a Payment Link (a URL to open separately, or
// paste and share) -- never a fixed-price "Pay Now" button a customer
// completes without leaving the page. See orchestrator/
// payment_gateway_manager.py's create_razorpay_order() +
// verify_razorpay_checkout_signature() for the real Orders API call and
// the security-required signature check behind this.
declare global {
  interface Window {
    Razorpay: new (options: Record<string, unknown>) => { open: () => void };
  }
}

// PRICING REVISED 2026-09-09 (founder direct instruction): reverses the
// 2026-08-24 "fair-market, not bargain-bin, because we want to be
// trusted" reasoning below -- founder's own call this time is that
// ₹6,999/₹17,999 is too high with zero paying customers/case studies to
// point to yet. This is real "founding customer" launch pricing:
// explicitly introductory, meant to rise once real track record exists,
// not a permanent bargain-bin position. Same ~3x ratio between tiers
// kept intentionally.
//
// Original 2026-08-24 reasoning, kept for context: "take whatever's
// running in market, take average than low cost, because we are new."
// Grounded in a real search (AI agent/ops SaaS for small businesses/
// agencies, 2026): narrow single-workflow bots start near $0-50/mo, but
// agency-deployed multi-workflow agent teams run $300-1,500/mo per
// client in the US market -- the wrong comparable to import directly,
// prices out the actual target buyer here (small Indian agencies).
const TIERS = [
  { id: "blackboxops_os_starter", name: "Starter", price: 2999, period: " one-time", desc: "Core agent team — CEO, Sentinel, Security, Finance — for one business. First 300 founding customers only." },
  { id: "blackboxops_os_growth", name: "Growth", price: 7999, period: " one-time", desc: "Everything in Starter, plus Chrome Developer, Website Builder, Worker Pool, and ERT. First 300 founding customers only." },
];

export default function BlackboxPricingPage() {
  // REMOVED 2026-09-09 (founder instruction: "remove payu link its
  // manual, make Razorpay fix price after click gateway"): the standalone
  // "Pay Now" card used a static link the founder created by hand in his
  // PayU dashboard -- a fixed amount that could drift from whatever the
  // tier cards actually charge, and not tied to a specific tier at all.
  // Razorpay is now the default gateway below: click a tier's "Pay Now"
  // and it goes straight into Razorpay's own Checkout modal for that
  // tier's exact price -- no separate link, nothing to keep in sync by
  // hand. PayU's own real hash-signed checkout (payWithRazorpayCheckout's
  // sibling, subscribePayu below) is left in place as a selectable
  // option, not removed -- what's gone is only the manual static link.
  const [gateway, setGateway] = useState<"razorpay" | "payu">("razorpay");
  const [email, setEmail] = useState("");
  const [razorpayKeyId, setRazorpayKeyId] = useState("");
  const [razorpaySecret, setRazorpaySecret] = useState("");
  const [payuKey, setPayuKey] = useState("");
  const [payuSalt, setPayuSalt] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ checkout?: string | { action_url: string; fields: Record<string, string> } } | null>(null);
  const [paidTier, setPaidTier] = useState<string | null>(null);
  const [razorpayReady, setRazorpayReady] = useState(false);

  // PayU's hash-signed form is already a real fixed-price checkout (no
  // link, one exact amount) -- this stays as-is, just needs real merchant
  // key+salt (a founder credential gap, not a code gap).
  async function subscribePayu(product: string) {
    if (!email) { setError("Enter an email first."); setStatus("error"); return; }
    setStatus("loading"); setError(""); setResult(null);
    try {
      const res = await fetch("/api/blackboxops/subscribe", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, product, gateway: "payu", payuKey, payuSalt }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed");
      setResult(data);
      setStatus("idle");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setStatus("error");
    }
  }

  // The real fix: a fixed-price Order created for this exact tier's exact
  // amount, opened directly in Razorpay's own Checkout modal -- no link
  // generated, nothing to copy or share, payment completes on this page.
  async function payWithRazorpayCheckout(tier: { id: string; name: string; price: number }) {
    if (!razorpayReady || !window.Razorpay) {
      setError("Razorpay Checkout is still loading — try again in a moment.");
      setStatus("error");
      return;
    }
    setStatus("loading"); setError(""); setResult(null);
    try {
      const orderRes = await fetch("/api/blackboxops/razorpay-order", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amountInr: tier.price, receipt: `${tier.id}_${Date.now()}`, product: tier.id, razorpayKeyId, razorpaySecret }),
      });
      const order = await orderRes.json();
      if (!orderRes.ok) throw new Error(order.error || "Could not create order");

      setStatus("idle");
      const rzp = new window.Razorpay({
        key: order.keyId,
        order_id: order.order_id,
        amount: order.amount,
        currency: order.currency,
        name: "blackboxOps_OS",
        description: `${tier.name} — ₹${tier.price.toLocaleString("en-IN")}/month`,
        prefill: email ? { email } : undefined,
        theme: { color: "#dba956" },
        handler: async (response: { razorpay_payment_id: string; razorpay_order_id: string; razorpay_signature: string }) => {
          try {
            const verifyRes = await fetch("/api/blackboxops/razorpay-verify", {
              method: "POST", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                orderId: response.razorpay_order_id, paymentId: response.razorpay_payment_id,
                signature: response.razorpay_signature, razorpaySecret,
              }),
            });
            const verified = await verifyRes.json();
            if (!verifyRes.ok || !verified.verified) throw new Error(verified.error || "Payment could not be verified");
            setPaidTier(tier.name);
          } catch (e) {
            setError(e instanceof Error ? e.message : "Payment succeeded but could not be verified — contact support.");
            setStatus("error");
          }
        },
        modal: { ondismiss: () => setStatus("idle") },
      });
      rzp.open();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setStatus("error");
    }
  }

  return (
    <div className="fixed inset-0 overflow-y-auto" style={{ background: "#0a0c10", color: "#e8ecf1" }}>
      <Script src="https://checkout.razorpay.com/v1/checkout.js" onLoad={() => setRazorpayReady(true)} />
      <div className="max-w-4xl mx-auto px-8 py-10">
        <Link href="/blackboxops-os" className="text-xs font-mono text-[#8b95a6] hover:text-white">← blackboxOps_OS</Link>
        <h1 className="text-3xl font-semibold mt-4 mb-2">Pricing</h1>
        <p className="text-sm text-[#a8b1c2] mb-2">
          Founding-customer launch pricing — real, discounted while we build our first track record. Locked in for early customers.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 my-8">
          {TIERS.map((t) => (
            <div key={t.id} className="rounded-xl border border-[#1e232e] p-6" style={{ background: "#0f131a" }}>
              <div className="text-lg font-semibold">{t.name}</div>
              <div className="mt-2 mb-3">
                <span className="text-3xl font-semibold">₹{t.price.toLocaleString("en-IN")}</span>
                <span className="text-sm text-[#8b95a6]">{t.period}</span>
              </div>
              <p className="text-sm text-[#a8b1c2] mb-5">{t.desc}</p>
              {paidTier === t.name ? (
                <div className="w-full rounded-lg py-2.5 text-sm font-medium text-center" style={{ background: "#4ade8022", color: "#4ade80", border: "1px solid #4ade8055" }}>
                  ✓ Paid — welcome to {t.name}
                </div>
              ) : (
                <button
                  onClick={() => (gateway === "razorpay" ? payWithRazorpayCheckout(t) : subscribePayu(t.id))}
                  disabled={status === "loading" || (gateway === "razorpay" && !razorpayReady)}
                  className="w-full rounded-lg py-2.5 text-sm font-medium disabled:opacity-50"
                  style={{ background: "#dba956", color: "#0a0c10" }}
                >
                  {status === "loading"
                    ? "Preparing checkout…"
                    : gateway === "razorpay"
                    ? `Pay ₹${t.price.toLocaleString("en-IN")} now`
                    : `Pay ₹${t.price.toLocaleString("en-IN")} once`}
                </button>
              )}
            </div>
          ))}
        </div>

        <div className="rounded-xl border border-[#1e232e] p-5 mb-8" style={{ background: "#0f131a" }}>
          <div className="text-xs font-mono uppercase tracking-wide text-[#8b95a6] mb-3">Checkout details</div>
          <input
            type="email" placeholder="customer email" value={email} onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-[#2a3040] bg-[#0a0c10] px-3 py-2 text-sm mb-3"
          />
          <div className="flex gap-2 mb-3">
            <button onClick={() => setGateway("payu")} className={`text-xs px-3 py-1.5 rounded-full border ${gateway === "payu" ? "border-[#dba956] text-[#dba956]" : "border-[#2a3040] text-[#8b95a6]"}`}>PayU</button>
            <button onClick={() => setGateway("razorpay")} className={`text-xs px-3 py-1.5 rounded-full border ${gateway === "razorpay" ? "border-[#dba956] text-[#dba956]" : "border-[#2a3040] text-[#8b95a6]"}`}>Razorpay</button>
          </div>

          {error && <p className="text-xs text-[#f87171] mb-3">{error}</p>}
          {gateway === "razorpay" && (
            <p className="text-xs text-[#5b6472] mb-3">
              Razorpay opens its own Checkout modal directly on this page for the tier&rsquo;s exact price — no payment link is generated or shared.
            </p>
          )}
          {result?.checkout && typeof result.checkout === "object" && (
            <p className="text-xs text-[#4ade80] mb-3">PayU checkout form prepared (txnid ready) — a real page would auto-submit this to PayU.</p>
          )}
        </div>

        <details className="rounded-xl border border-[#1e232e] p-5" style={{ background: "#0f131a" }}>
          <summary className="text-xs font-mono uppercase tracking-wide text-[#8b95a6] cursor-pointer">
            Founder test mode — merchant credentials (staging only)
          </summary>
          <p className="text-xs text-[#a8b1c2] my-3">
            A real customer never sees this. In production, merchant credentials live server-side (environment
            variables), never in the checkout request from a customer&apos;s browser. This panel exists only so you can
            test the real checkout flow today, on staging, before that server-side config exists.
          </p>
          {gateway === "razorpay" ? (
            <div className="grid grid-cols-2 gap-2">
              <input placeholder="Razorpay Key ID" value={razorpayKeyId} onChange={(e) => setRazorpayKeyId(e.target.value)} className="rounded-lg border border-[#2a3040] bg-[#0a0c10] px-3 py-2 text-xs" />
              <input placeholder="Razorpay Key Secret" type="password" value={razorpaySecret} onChange={(e) => setRazorpaySecret(e.target.value)} className="rounded-lg border border-[#2a3040] bg-[#0a0c10] px-3 py-2 text-xs" />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <input placeholder="PayU Merchant Key" value={payuKey} onChange={(e) => setPayuKey(e.target.value)} className="rounded-lg border border-[#2a3040] bg-[#0a0c10] px-3 py-2 text-xs" />
              <input placeholder="PayU Merchant Salt" type="password" value={payuSalt} onChange={(e) => setPayuSalt(e.target.value)} className="rounded-lg border border-[#2a3040] bg-[#0a0c10] px-3 py-2 text-xs" />
            </div>
          )}
        </details>

        <p className="text-xs text-[#5b6472] mt-8">
          Questions before you pay? Email{" "}
          <a href={`mailto:${SUPPORT_EMAIL}`} className="text-[#dba956] hover:underline">{SUPPORT_EMAIL}</a>
        </p>
      </div>
    </div>
  );
}
