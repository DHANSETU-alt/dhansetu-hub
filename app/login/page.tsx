import { Suspense } from "react";
import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return <main className="min-h-screen bg-slate-50 px-4 py-16"><Suspense fallback={<p className="text-center">Loading…</p>}><LoginForm /></Suspense></main>;
}
