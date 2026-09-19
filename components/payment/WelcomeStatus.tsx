"use client";

import { useEffect, useState } from "react";

export function WelcomeStatus({ orderId }: { orderId: string }) {
  const [timedOut, setTimedOut] = useState(false);
  useEffect(() => {
    const started = Date.now();
    const poll = async () => {
      const response = await fetch("/api/entitlement", { cache: "no-store" });
      if (response.ok) {
        const body = await response.json();
        if (body.active) { location.replace(body.appUrl); return; }
      }
      if (Date.now() - started >= 60_000) { setTimedOut(true); return; }
      window.setTimeout(poll, 2_000);
    };
    void poll();
  }, []);
  return <section className="mx-auto max-w-lg rounded-2xl bg-white p-8 text-center shadow-sm"><div className="mx-auto mb-5 h-10 w-10 animate-spin rounded-full border-4 border-emerald-600 border-t-transparent" /><h1 className="text-3xl font-bold">Payment received, activating your account</h1><p className="mt-3 text-slate-600">Keep this page open. You will enter DhanSetu Hub automatically.</p>{timedOut && <div className="mt-6 rounded-lg bg-amber-50 p-4 text-left text-sm"><p>Activation is taking longer than expected. Email <a className="underline" href={`mailto:support@dhansetuhub.in?subject=Activation ${orderId}`}>support@dhansetuhub.in</a> with order reference <strong>{orderId}</strong>.</p></div>}</section>;
}
