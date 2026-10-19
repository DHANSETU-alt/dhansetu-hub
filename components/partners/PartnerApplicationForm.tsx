"use client";

import { useState } from "react";

type PartnerKind = "affiliate" | "tax_provider" | "gst_provider" | "career_provider" | "insurance_partner";

export function PartnerApplicationForm({ initialKind = "affiliate" }: { initialKind?: PartnerKind }) {
  const [kind, setKind] = useState<PartnerKind>(initialKind);
  const [displayName, setDisplayName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [notes, setNotes] = useState("");
  const [disclosureAccepted, setDisclosureAccepted] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setMessage("");
    const response = await fetch("/api/partners/apply", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ kind, displayName, contactEmail, notes, disclosureAccepted }) });
    const result = await response.json() as { error?: string };
    setBusy(false); setMessage(response.ok ? "Application received. It remains pending review; no partner status or payout is created automatically." : result.error ?? "Application failed");
    if (response.ok) { setDisplayName(""); setContactEmail(""); setNotes(""); setDisclosureAccepted(false); }
  }

  return <form className="space-y-4 rounded-2xl border bg-white p-5 shadow-sm" onSubmit={submit}><label className="block text-sm font-medium">Partner type<select className="mt-2 w-full rounded-xl border p-3" value={kind} onChange={(event) => setKind(event.target.value as PartnerKind)}><option value="affiliate">Software affiliate</option><option value="tax_provider">Qualified tax professional</option><option value="gst_provider">Qualified GST professional</option><option value="career_provider">Career professional</option><option value="insurance_partner">Licensed insurance partner</option></select></label><label className="block text-sm font-medium">Name or business<input className="mt-2 w-full rounded-xl border p-3" required value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label><label className="block text-sm font-medium">Contact email<input className="mt-2 w-full rounded-xl border p-3" required type="email" value={contactEmail} onChange={(event) => setContactEmail(event.target.value)} /></label><label className="block text-sm font-medium">Relevant experience or disclosure<textarea className="mt-2 min-h-24 w-full rounded-xl border p-3" value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={2000} /></label><label className="flex items-start gap-3 text-sm text-slate-700"><input className="mt-1" type="checkbox" required checked={disclosureAccepted} onChange={(event) => setDisclosureAccepted(event.target.checked)} /><span>I understand this is an application only. DhanSetu does not automatically verify partners, authorize regulated advice, publish commission terms, or initiate payouts.</span></label><button className="rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white disabled:opacity-50" disabled={busy} type="submit">{busy ? "Submitting…" : "Submit for review"}</button>{message && <p className="text-sm text-slate-700" role="status">{message}</p>}</form>;
}
