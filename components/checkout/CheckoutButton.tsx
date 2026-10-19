"use client";

import Script from "next/script";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import type { TierId } from "@/lib/payment/tiers";

declare global { interface Window { Razorpay: new (options: Record<string, unknown>) => { open(): void } } }

export function CheckoutButton({ tier, email }: { tier: TierId; email: string }) {
  const router = useRouter();
  const inFlight = useRef(false);
  const paymentReceived = useRef(false);
  const [scriptReady, setScriptReady] = useState(false);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function pay() {
    if (inFlight.current) return;
    if (!consent) return setError("Accept the policies before continuing.");
    if (!scriptReady || !window.Razorpay) return setError("Secure checkout is still loading. Please try again shortly.");
    inFlight.current = true;
    paymentReceived.current = false;
    setBusy(true); setError("");
    try {
      const response = await fetch("/api/checkout/create-order", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ tier, consent: true }) });
      const order = await response.json();
      if (!response.ok) throw new Error(order.error ?? "Could not start checkout");
      if (order.existingAccess || order.recovery) {
        router.push(`/welcome?order=${encodeURIComponent(order.orderId)}`);
        return;
      }
      const razorpay = new window.Razorpay({
        key: order.keyId, order_id: order.orderId, amount: order.amount, currency: order.currency,
        name: "DhanSetu Hub", description: "Lifetime access", prefill: { email },
        handler: async (payment: Record<string, string>) => {
          paymentReceived.current = true;
          try {
            const verify = await fetch("/api/checkout/verify", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payment) });
            if (!verify.ok) throw new Error("Verification is pending");
          } catch {
            // Continue recovery for this order; never invite a second payment.
          }
          router.push(`/welcome?order=${encodeURIComponent(order.orderId)}`);
        },
        modal: { ondismiss: () => {
          if (!paymentReceived.current) { inFlight.current = false; setBusy(false); }
        } }, theme: { color: "#059669" },
      });
      razorpay.open();
    } catch (error) {
      inFlight.current = false;
      setBusy(false);
      setError(error instanceof Error ? error.message : "Could not open secure checkout. Please try again.");
    }
  }

  return <div className="space-y-4">
    <Script src="https://checkout.razorpay.com/v1/checkout.js" strategy="afterInteractive" onReady={() => setScriptReady(true)} onError={() => { setScriptReady(false); setError("Secure checkout could not load. Check your connection and reload this page."); }} />
    <label className="flex items-start gap-3 text-sm"><input className="mt-1" type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /><span>I agree to the <a className="underline" href="/terms">Terms</a>, <a className="underline" href="/privacy">Privacy Policy</a> and <a className="underline" href="/refund">Refund Policy</a>.</span></label>
    {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
    <button onClick={pay} disabled={!consent || busy || !scriptReady} className="w-full rounded-xl bg-emerald-600 px-5 py-4 font-bold text-white disabled:cursor-not-allowed disabled:opacity-50">{busy ? "Opening secure checkout…" : "Pay securely with Razorpay"}</button>
    <p className="text-xs text-slate-500">Instant digital delivery. See our <a href="/delivery" className="underline">delivery policy</a> and <a href="/contact" className="underline">contact details</a>.</p>
  </div>;
}
