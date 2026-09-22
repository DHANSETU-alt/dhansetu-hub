"use client";

import { FormEvent, useEffect, useState } from "react";
import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createBrowserSupabase } from "@/lib/supabase/client";

function PasswordResetForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const next = params.get("next");
  const destination = next?.startsWith("/") && !next.startsWith("//") ? next : "/";

  useEffect(() => {
    const supabase = createBrowserSupabase();
    let active = true;
    void supabase.auth.getSession().then(({ data }) => { if (active) setReady(Boolean(data.session)); });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      if (active) setReady(Boolean(session));
    });
    return () => { active = false; listener.subscription.unsubscribe(); };
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (password.length < 8) return setMessage("Use at least 8 characters.");
    if (password !== confirmation) return setMessage("Passwords do not match.");
    setBusy(true); setMessage("");
    const { error } = await createBrowserSupabase().auth.updateUser({ password });
    setBusy(false);
    if (error) return setMessage(error.message);
    setMessage("Password updated. Redirecting…");
    router.replace(destination);
    router.refresh();
  }

  return <main className="min-h-screen bg-slate-50 px-4 py-16"><form onSubmit={submit} className="mx-auto max-w-md space-y-5 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm"><h1 className="text-3xl font-bold text-slate-950">Set a new password</h1><p className="text-sm text-slate-600">This secure link changes only your DhanSetu account password.</p><label className="block text-sm font-medium">New password<input className="mt-1 w-full rounded-lg border p-3" type="password" minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} /></label><label className="block text-sm font-medium">Confirm password<input className="mt-1 w-full rounded-lg border p-3" type="password" minLength={8} required value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></label>{message && <p role="alert" className="text-sm text-slate-700">{message}</p>}<button disabled={busy || !ready} className="w-full rounded-lg bg-emerald-600 p-3 font-semibold text-white disabled:opacity-50">{!ready ? "Opening secure link…" : busy ? "Updating…" : "Update password"}</button>{!ready && <p className="text-xs text-slate-500">If this page was opened without a reset link, request a new one from the sign-in page.</p>}</form></main>;
}

export default function PasswordResetPage() {
  return <Suspense fallback={<main className="min-h-screen bg-slate-50 px-4 py-16"><p className="mx-auto max-w-md text-center text-slate-600">Opening secure link…</p></main>}><PasswordResetForm /></Suspense>;
}
