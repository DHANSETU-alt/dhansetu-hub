"use client";

import { useEffect, useState } from "react";

export function WelcomeStatus({ orderId }: { orderId: string }) {
  const [timedOut, setTimedOut] = useState(false);
  useEffect(() => {
    const started = Date.now();
    let cancelled = false;
    let timer: number | undefined;
    const controller = new AbortController();
    const poll = async () => {
      try {
        const response = await fetch(`/api/entitlement?order=${encodeURIComponent(orderId)}`, { cache: "no-store", signal: AbortSignal.any([controller.signal, AbortSignal.timeout(8000)]) });
        if (response.ok) {
          const body = await response.json();
          if (!cancelled && body.active) { location.replace(body.appUrl); return; }
        }
      } catch {
        // Network interruptions do not end recovery or justify another payment.
      }
      if (cancelled) return;
      if (Date.now() - started >= 60_000) { setTimedOut(true); return; }
      timer = window.setTimeout(poll, 2_000);
    };
    void poll();
    return () => { cancelled = true; controller.abort(); if (timer) window.clearTimeout(timer); };
  }, [orderId]);
  return <section className="mx-auto max-w-lg rounded-2xl bg-white p-8 text-center shadow-sm"><div className="mx-auto mb-5 h-10 w-10 animate-spin rounded-full border-4 border-emerald-600 border-t-transparent" /><h1 className="text-3xl font-bold">Checking payment and account access</h1><p className="mt-3 text-slate-600">Keep this page open while we check your account. If you have paid, do not pay again.</p>{timedOut && <div className="mt-6 rounded-lg bg-amber-50 p-4 text-left text-sm"><p>Activation is taking longer than expected. Check <a className="underline" href="/billing">Billing</a> or email <a className="underline" href={`mailto:support@dhansetuhub.in?subject=${encodeURIComponent(`Activation ${orderId}`)}`}>support@dhansetuhub.in</a> with order reference <strong>{orderId}</strong>. Do not make another payment for this order.</p></div>}</section>;
}
