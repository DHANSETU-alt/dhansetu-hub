"use client";

import Script from "next/script";
import { useState } from "react";
import type { TierId } from "@/lib/payment/tiers";

declare global { interface Window { Razorpay: new (options: Record<string, unknown>) => { open(): void } } }

export function CheckoutButton({ tier, email }: { tier: TierId; email: string }) {
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function pay() {
    if (!consent) return setError("Accept the policies before continuing.");
    setBusy(true); setError("");
    const response = await fetch("/api/checkout/create-order", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ tier, consent: true }) });
    const order = await response.json();
    if (!response.ok) { setBusy(false); return setError(order.error ?? "Could not start checkout"); }
    const razorpay = new window.Razorpay({
      key: order.keyId, order_id: order.orderId, amount: order.amount, currency: order.currency,
      name: "DhanSetu Hub", description: "Lifetime access", prefill: { email },
      handler: async (payment: Record<string, string>) => {
        const verify = await fetch("/api/checkout/verify", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payment) });
        if (!verify.ok) { const body = await verify.json(); setBusy(false); return setError(body.error ?? "Verification failed"); }
        location.assign(`/welcome?order=${encodeURIComponent(order.orderId)}`);
      },
      modal: { ondismiss: () => setBusy(false) }, theme: { color: "#059669" },
    });
    razorpay.open();
  }

  return <div className="space-y-4">
    <Script src="https://checkout.razorpay.com/v1/checkout.js" strategy="afterInteractive" />
    <label className="flex items-start gap-3 text-sm"><input className="mt-1" type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /><span>I agree to the <a className="underline" href="/terms">Terms</a>, <a className="underline" href="/privacy">Privacy Policy</a> and <a className="underline" href="/refund">Refund Policy</a>.</span></label>
    {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
    <button onClick={pay} disabled={!consent || busy} className="w-full rounded-xl bg-emerald-600 px-5 py-4 font-bold text-white disabled:cursor-not-allowed disabled:opacity-50">{busy ? "Opening secure checkout…" : "Pay securely with Razorpay"}</button>
    <p className="text-xs text-slate-500">Instant digital delivery. See our <a href="/delivery" className="underline">delivery policy</a> and <a href="/contact" className="underline">contact details</a>.</p>
  </div>;
}
