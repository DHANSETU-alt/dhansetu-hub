"use client";

import { useState } from "react";
import { reconcileGst, type GstInvoice } from "@/lib/gst/reconcile";

function parseCsv(text: string): GstInvoice[] {
  const rows = text.trim().split(/\r?\n/).filter(Boolean);
  if (rows.length < 2) return [];
  const headers = rows[0].split(",").map((value) => value.trim().toLowerCase().replace(/[^a-z]/g, ""));
  const find = (...names: string[]) => headers.findIndex((header) => names.includes(header));
  const invoiceIndex = find("invoicenumber", "invoiceno", "documentnumber");
  const gstinIndex = find("suppliergstin", "gstin");
  const taxableIndex = find("taxablevalue", "taxableamount");
  const taxIndex = find("totaltax", "taxamount", "igstcgstsgst");
  if (invoiceIndex < 0 || taxableIndex < 0 || taxIndex < 0) return [];
  return rows.slice(1).flatMap((line) => {
    const cells = line.split(",");
    const invoiceNumber = cells[invoiceIndex]?.trim();
    const supplierGstin = cells[gstinIndex]?.trim() || "UNKNOWN";
    const taxableValuePaise = Math.round(Number(cells[taxableIndex]?.replace(/[₹,\s]/g, "")) * 100);
    const taxPaise = Math.round(Number(cells[taxIndex]?.replace(/[₹,\s]/g, "")) * 100);
    return invoiceNumber && Number.isFinite(taxableValuePaise) && Number.isFinite(taxPaise) ? [{ invoiceNumber, supplierGstin, taxableValuePaise, taxPaise }] : [];
  });
}

export default function GstPage() {
  const [register, setRegister] = useState<GstInvoice[]>([]);
  const [statement, setStatement] = useState<GstInvoice[]>([]);
  const [message, setMessage] = useState("Load both CSV exports to reconcile locally.");
  const result = reconcileGst(register, statement);

  async function load(file: File | undefined, kind: "register" | "statement") {
    if (!file) return;
    const parsed = parseCsv(await file.text());
    if (kind === "register") setRegister(parsed); else setStatement(parsed);
    setMessage(`${parsed.length} rows loaded locally from ${file.name}.`);
  }

  function exportReview() {
    const rows = ["invoice_number,supplier_gstin,reason", ...result.review.map((item) => [item.invoiceNumber, item.supplierGstin, item.reason].map((cell) => JSON.stringify(cell)).join(","))];
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([rows.join("\n")], { type: "text/csv" }));
    link.download = "dhansetu-gst-review.csv";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function clearImportedData() {
    setRegister([]); setStatement([]); setMessage("Imported statements cleared from this browser.");
  }

  return <main className="mx-auto min-h-screen max-w-5xl space-y-8 bg-slate-50 px-5 py-12 text-slate-950">
    <header><p className="text-xs font-bold uppercase tracking-[.2em] text-emerald-700">DhanSetu · review workspace</p><h1 className="mt-3 text-4xl font-black tracking-tight">GST LeakShield</h1><p className="mt-3 max-w-2xl text-slate-600">Compare purchase-register rows with GSTR-2B exports without uploading them. Review mismatches with your CA or tax professional.</p></header>
    <section className="grid gap-5 md:grid-cols-2"><label className="rounded-2xl border-2 border-dashed border-emerald-300 bg-white p-6 text-sm font-semibold">Purchase register CSV<input className="mt-4 block w-full text-sm" type="file" accept=".csv" onChange={(event) => void load(event.target.files?.[0], "register")} /></label><label className="rounded-2xl border-2 border-dashed border-blue-300 bg-white p-6 text-sm font-semibold">GSTR-2B CSV<input className="mt-4 block w-full text-sm" type="file" accept=".csv" onChange={(event) => void load(event.target.files?.[0], "statement")} /></label></section>
    <p className="text-sm text-slate-600" aria-live="polite">{message}</p>
    <section className="grid gap-4 sm:grid-cols-3"><article className="rounded-2xl bg-slate-950 p-5 text-white"><span className="text-xs text-slate-400">Matched rows</span><strong className="mt-2 block text-3xl text-emerald-300">{result.matched}</strong></article><article className="rounded-2xl border bg-white p-5"><span className="text-xs text-slate-500">Review items</span><strong className="mt-2 block text-3xl">{result.review.length}</strong></article><article className="rounded-2xl border border-amber-200 bg-amber-50 p-5"><span className="text-xs text-amber-700">Amount requiring review</span><strong className="mt-2 block text-3xl">₹{(result.amountRequiringReviewPaise / 100).toLocaleString("en-IN")}</strong></article></section>
    <section className="rounded-2xl border bg-white p-6"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-xl font-semibold">Review queue</h2><div className="flex gap-2"><button type="button" className="rounded-lg bg-slate-950 px-3 py-2 text-sm font-semibold text-white" onClick={exportReview} disabled={!result.review.length}>Download review CSV</button><button type="button" className="rounded-lg border px-3 py-2 text-sm font-semibold" onClick={clearImportedData} disabled={!register.length && !statement.length}>Clear imported data</button></div></div>{result.review.length ? <ul className="mt-4 divide-y">{result.review.map((item) => <li className="flex flex-wrap justify-between gap-2 py-3 text-sm" key={`${item.supplierGstin}-${item.invoiceNumber}-${item.reason}`}><span><b>{item.invoiceNumber}</b> · {item.supplierGstin}</span><span className="text-amber-700">{item.reason.replaceAll("_", " ")}</span></li>)}</ul> : <p className="mt-4 text-sm text-slate-500">No review items yet. Both files must be loaded before a match can be meaningful.</p>}<p className="mt-5 border-t pt-4 text-xs text-slate-500">{result.note} Local browser processing only; no GST filing is performed.</p></section>
  </main>;
}
