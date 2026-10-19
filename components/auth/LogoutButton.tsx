"use client";

import { useRouter } from "next/navigation";
import { createBrowserSupabase } from "@/lib/supabase/client";

export function LogoutButton() {
  const router = useRouter();
  async function logout() {
    await createBrowserSupabase().auth.signOut();
    router.replace("/");
    router.refresh();
  }
  return <button type="button" onClick={() => void logout()} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Sign out</button>;
}
