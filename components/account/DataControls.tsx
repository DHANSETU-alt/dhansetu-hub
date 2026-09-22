"use client";

import { useState } from "react";

export function DataControls() {
  const [confirmation, setConfirmation] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  async function deleteData() {
    if (confirmation !== "DELETE_MY_DATA") return setMessage("Type DELETE_MY_DATA exactly to continue.");
    setBusy(true); setMessage("");
    const response = await fetch("/api/account/data", { method: "DELETE", headers: { "content-type": "application/json" }, body: JSON.stringify({ confirmation }) });
    const payload = await response.json().catch(() => ({})) as { error?: string };
    setBusy(false);
    setMessage(response.ok ? "Personal workspace data deleted. Verified payment records were retained for billing and legal accounting." : payload.error ?? "Deletion failed.");
    if (response.ok) setConfirmation("");
  }
  return <section className="rounded-2xl border border-rose-200 bg-rose-50 p-6"><h2 className="text-xl font-semibold text-rose-950">Delete personal workspace data</h2><p className="mt-2 text-sm text-rose-900">This removes SmartBudget transactions, saved tax/GST records, and partner applications. Verified payment and entitlement records remain for billing, fraud prevention, and legal accounting.</p><label className="mt-4 block text-sm font-semibold text-rose-950">Type DELETE_MY_DATA to confirm<input className="mt-2 w-full rounded-xl border border-rose-300 bg-white p-3" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} autoComplete="off" /></label><button type="button" disabled={busy || confirmation !== "DELETE_MY_DATA"} onClick={() => void deleteData()} className="mt-4 rounded-xl bg-rose-700 px-4 py-3 font-semibold text-white disabled:opacity-50">{busy ? "Deleting…" : "Delete workspace data"}</button>{message && <p role="status" className="mt-3 text-sm text-rose-900">{message}</p>}</section>;
}
