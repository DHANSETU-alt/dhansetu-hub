import { redirect } from "next/navigation";
import { ResumeWorkspace } from "@/components/resume/ResumeWorkspace";
import { createServerSupabase } from "@/lib/supabase/server";
import { hasEntitlement } from "@/lib/payment/entitlement";

export const dynamic = "force-dynamic";

export default async function ResumeAiPage() {
  const supabase = await createServerSupabase();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect("/login?next=/resume-ai");
  const entitled = await hasEntitlement(data.user.id);
  return <main className="mx-auto max-w-3xl space-y-6 p-5 sm:p-8"><div><p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">Career workspace</p><h1 className="mt-2 text-3xl font-bold text-slate-900">Resume AI</h1><p className="mt-2 text-slate-600">Reconstruct an old resume into editable ATS-friendly text and compare it with a job description. Results are assistive, not an authoritative ATS score.</p></div>{entitled ? <ResumeWorkspace /> : <section className="rounded-2xl border bg-white p-6"><h2 className="text-xl font-semibold">An active plan is required</h2><p className="mt-2 text-slate-600">Your account is signed in, but this protected career workspace is not included yet.</p><a className="mt-4 inline-block rounded-xl bg-emerald-600 px-5 py-3 font-semibold text-white" href="/checkout?tier=all_access">View DhanSetu All Access</a></section>}</main>;
}
