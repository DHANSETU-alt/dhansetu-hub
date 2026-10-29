"use client";

import { useState } from "react";

export function FounderSheetSync() {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function sync() {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch("/api/founder/sheets/sync", { method: "POST", credentials: "same-origin" });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || "Sync failed");
      setMessage(`Synced ${payload.rowsWritten ?? 0} rows across ${payload.tabs?.length ?? 0} private tabs.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Sync failed");
    } finally {
      setBusy(false);
    }
  }

  return <section className="mt-6 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 p-5" aria-labelledby="founder-sheet-sync-title">
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h2 id="founder-sheet-sync-title" className="font-bold">Private founder ledger sync</h2>
        <p className="mt-2 text-sm text-emerald-50/80">Server-only service account. Customer sheets and customer memory are never copied here.</p>
      </div>
      <button type="button" onClick={() => void sync()} disabled={busy} className="rounded-xl bg-emerald-300 px-4 py-2 font-semibold text-slate-950 disabled:opacity-50">{busy ? "Syncing…" : "Sync to Google Sheet"}</button>
    </div>
    {message && <p role="status" className="mt-3 text-sm text-emerald-50">{message}</p>}
  </section>;
}
