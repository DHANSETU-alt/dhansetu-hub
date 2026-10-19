"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createBrowserSupabase } from "@/lib/supabase/client";

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "signup" | "reset">("login");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const next = params.get("next");
  const destination = next?.startsWith("/") && !next.startsWith("//") ? next : "/checkout?tier=smartbudget_pro";

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage("");
    const supabase = createBrowserSupabase();
    if (mode === "reset") {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${location.origin}/auth/reset?next=${encodeURIComponent(destination)}`,
      });
      setBusy(false);
      if (error) return setMessage(error.message);
      return setMessage("Check your email for a secure password-reset link.");
    }
    const result = mode === "login"
      ? await supabase.auth.signInWithPassword({ email, password })
      : await supabase.auth.signUp({ email, password, options: { emailRedirectTo: `${location.origin}${destination}` } });
    setBusy(false);
    if (result.error) return setMessage(result.error.message);
    if (mode === "signup" && !result.data.session) return setMessage("Check your email to confirm your account, then return here to sign in.");
    router.replace(destination); router.refresh();
  }

  async function signInWithGoogle() {
    setBusy(true); setMessage("");
    const supabase = createBrowserSupabase();
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${location.origin}/auth/callback?next=${encodeURIComponent(destination)}` },
    });
    if (error) { setBusy(false); setMessage(error.message); }
  }

  return <form onSubmit={submit} className="mx-auto max-w-md space-y-5 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
    <h1 className="text-3xl font-bold text-slate-950">{mode === "login" ? "Sign in before payment" : mode === "signup" ? "Create your account" : "Reset your password"}</h1>
    <p className="text-sm text-slate-600">{mode === "reset" ? "We will email a secure link to restore access to your account." : "Your purchase is permanently attached to this account."}</p>
    <label className="block text-sm font-medium">Email<input className="mt-1 w-full rounded-lg border p-3" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
    {mode !== "reset" && <label className="block text-sm font-medium">Password<input className="mt-1 w-full rounded-lg border p-3" type="password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} /></label>}
    {message && <p role="alert" className="text-sm text-rose-700">{message}</p>}
    <button disabled={busy} className="w-full rounded-lg bg-emerald-600 p-3 font-semibold text-white disabled:opacity-50">{busy ? "Please wait…" : mode === "login" ? "Sign in" : mode === "signup" ? "Create account" : "Email reset link"}</button>
    {mode !== "reset" && <><div className="flex items-center gap-3 text-xs text-slate-400"><span className="h-px flex-1 bg-slate-200" />or<span className="h-px flex-1 bg-slate-200" /></div><button type="button" disabled={busy} onClick={() => void signInWithGoogle()} className="w-full rounded-lg border border-slate-300 bg-white p-3 font-semibold text-slate-800 disabled:opacity-50">Continue with Google</button></>}
    {mode === "login" && <button type="button" className="w-full text-sm text-emerald-700 underline" onClick={() => { setMessage(""); setMode("reset"); }}>Forgot password?</button>}
    <button type="button" className="w-full text-sm text-emerald-700 underline" onClick={() => { setMessage(""); setMode(mode === "login" || mode === "reset" ? "signup" : "login"); }}>{mode === "login" || mode === "reset" ? "New here? Create an account" : "Already registered? Sign in"}</button>
  </form>;
}
