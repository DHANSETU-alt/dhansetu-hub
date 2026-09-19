"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createBrowserSupabase } from "@/lib/supabase/client";

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const next = params.get("next");
  const destination = next?.startsWith("/") && !next.startsWith("//") ? next : "/checkout?tier=founding_lifetime";

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage("");
    const supabase = createBrowserSupabase();
    const result = mode === "login"
      ? await supabase.auth.signInWithPassword({ email, password })
      : await supabase.auth.signUp({ email, password, options: { emailRedirectTo: `${location.origin}${destination}` } });
    setBusy(false);
    if (result.error) return setMessage(result.error.message);
    if (mode === "signup" && !result.data.session) return setMessage("Check your email to confirm your account, then return here to sign in.");
    router.replace(destination); router.refresh();
  }

  return <form onSubmit={submit} className="mx-auto max-w-md space-y-5 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
    <h1 className="text-3xl font-bold text-slate-950">{mode === "login" ? "Sign in before payment" : "Create your account"}</h1>
    <p className="text-sm text-slate-600">Your purchase is permanently attached to this account.</p>
    <label className="block text-sm font-medium">Email<input className="mt-1 w-full rounded-lg border p-3" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
    <label className="block text-sm font-medium">Password<input className="mt-1 w-full rounded-lg border p-3" type="password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} /></label>
    {message && <p role="alert" className="text-sm text-rose-700">{message}</p>}
    <button disabled={busy} className="w-full rounded-lg bg-emerald-600 p-3 font-semibold text-white disabled:opacity-50">{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
    <button type="button" className="w-full text-sm text-emerald-700 underline" onClick={() => setMode(mode === "login" ? "signup" : "login")}>{mode === "login" ? "New here? Create an account" : "Already registered? Sign in"}</button>
  </form>;
}
