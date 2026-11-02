"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authClient } from "@/lib/better-auth-client";

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
  const authErrorMessage = (error: { message?: string } | null) => error?.message || "Authentication could not be completed. Try again.";

  useEffect(() => {
    const error = params.get("error");
    const messages: Record<string, string> = {
      auth_unavailable: "Sign-in is temporarily unavailable. Try again in a moment.",
      missing_auth_code: "Sign-in returned without an authorization code. Try again.",
      oauth_callback_failed: "Sign-in could not complete. Try email and password instead.",
      google_direct_not_configured: "Google sign-in is not configured yet. Email and password sign-in remains available.",
      google_direct_failed: "Google sign-in could not be completed. Please try email sign-in.",
    };
    if (error && messages[error]) setMessage(messages[error]);
  }, [params]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage("");
    if (mode === "reset") {
      const { error } = await authClient.requestPasswordReset({
        email,
        redirectTo: `${location.origin}/auth/reset?next=${encodeURIComponent(destination)}`,
      });
      setBusy(false);
      if (error) return setMessage(error.message ?? "Password reset could not be requested.");
      return setMessage("Check your email for a secure password-reset link.");
    }
    const result = mode === "login"
      ? await authClient.signIn.email({ email, password, callbackURL: destination })
      : await authClient.signUp.email({ email, password, name: email.split("@")[0], callbackURL: destination });
    setBusy(false);
    if (result.error) return setMessage(result.error.message ?? "Authentication could not be completed.");
    router.replace(destination); router.refresh();
  }

  async function signInWithGoogle() {
    setBusy(true); setMessage("");
    const { error } = await authClient.signIn.social({ provider: "google", callbackURL: destination });
    if (error) { setBusy(false); setMessage(authErrorMessage(error)); }
  }

  async function signInWithGitHub() {
    setBusy(true); setMessage("");
    const { error } = await authClient.signIn.social({ provider: "github", callbackURL: destination });
    if (error) { setBusy(false); setMessage(authErrorMessage(error)); }
  }

  return <form onSubmit={submit} className="mx-auto max-w-md space-y-5 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
    <h1 className="text-3xl font-bold text-slate-950">{mode === "login" ? "Sign in before payment" : mode === "signup" ? "Create your account" : "Reset your password"}</h1>
    <p className="text-sm text-slate-600">{mode === "reset" ? "We will email a secure link to restore access to your account." : "Your purchase is permanently attached to this account."}</p>
    <label className="block text-sm font-medium">Email<input className="mt-1 w-full rounded-lg border p-3" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
    {mode !== "reset" && <label className="block text-sm font-medium">Password<input className="mt-1 w-full rounded-lg border p-3" type="password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} /></label>}
    {message && <p role="alert" className="text-sm text-rose-700">{message}</p>}
    <button disabled={busy} className="w-full rounded-lg bg-emerald-600 p-3 font-semibold text-white disabled:opacity-50">{busy ? "Please wait…" : mode === "login" ? "Sign in" : mode === "signup" ? "Create account" : "Email reset link"}</button>
    {mode !== "reset" && <><div className="flex items-center gap-3 text-xs text-slate-400"><span className="h-px flex-1 bg-slate-200" />or<span className="h-px flex-1 bg-slate-200" /></div><button type="button" disabled={busy} onClick={() => void signInWithGoogle()} className="w-full rounded-lg border border-slate-300 bg-white p-3 font-semibold text-slate-800 disabled:opacity-50">Continue with Google</button><button type="button" disabled={busy} onClick={() => void signInWithGitHub()} className="w-full rounded-lg border border-slate-300 bg-slate-950 p-3 font-semibold text-white disabled:opacity-50">Continue with GitHub</button></>}
    {mode === "login" && <button type="button" className="w-full text-sm text-emerald-700 underline" onClick={() => { setMessage(""); setMode("reset"); }}>Forgot password?</button>}
    <button type="button" className="w-full text-sm text-emerald-700 underline" onClick={() => { setMessage(""); setMode(mode === "login" || mode === "reset" ? "signup" : "login"); }}>{mode === "login" || mode === "reset" ? "New here? Create an account" : "Already registered? Sign in"}</button>
  </form>;
}
