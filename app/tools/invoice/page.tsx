"use client";

import { useMemo, useState } from "react";

type Item = { description: string; quantity: number; rate: number };

const EMPTY_ITEM: Item = { description: "", quantity: 1, rate: 0 };
const inr = (amount: number) =>
  amount.toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });

export default function InvoiceGeneratorPage() {
  const today = new Date().toISOString().slice(0, 10);
  const [seller, setSeller] = useState({ name: "", gstin: "", address: "", phone: "", email: "" });
  const [buyer, setBuyer] = useState({ name: "", gstin: "", address: "" });
  const [meta, setMeta] = useState({ number: "INV-001", date: today, due: today, notes: "Payment due within 7 days." });
  const [gstRate, setGstRate] = useState(18);
  const [sameState, setSameState] = useState(true);
  const [items, setItems] = useState<Item[]>([{ ...EMPTY_ITEM }]);

  const totals = useMemo(() => {
    const subtotal = items.reduce((sum, item) => sum + item.quantity * item.rate, 0);
    const tax = (subtotal * gstRate) / 100;
    return { subtotal, tax, half: tax / 2, total: subtotal + tax };
  }, [items, gstRate]);

  const updateItem = (index: number, patch: Partial<Item>) =>
    setItems((current) => current.map((item, i) => (i === index ? { ...item, ...patch } : item)));

  const field = "w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600";
  const label = "mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500";

  return (
    <main className="mx-auto max-w-6xl p-6 print:p-0">
      <header className="mb-6 print:hidden">
        <p className="text-xs font-semibold uppercase tracking-widest text-emerald-700">Dhansetu Hub · free tool</p>
        <h1 className="mt-1 text-3xl font-bold text-slate-900">GST invoice generator</h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Fill in the details, check the preview, then save it as a PDF. Everything stays in your browser: nothing is
          uploaded and no sign-up is needed.
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-2">
        <form className="space-y-6 print:hidden" onSubmit={(event) => event.preventDefault()}>
          <section className="space-y-3 rounded-lg border border-slate-200 p-4">
            <h2 className="font-semibold text-slate-900">Your business</h2>
            <div>
              <label className={label} htmlFor="seller-name">Business name</label>
              <input id="seller-name" className={field} value={seller.name} onChange={(e) => setSeller({ ...seller, name: e.target.value })} placeholder="Soham Enterprise" />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className={label} htmlFor="seller-gstin">GSTIN (optional)</label>
                <input id="seller-gstin" className={field} value={seller.gstin} onChange={(e) => setSeller({ ...seller, gstin: e.target.value.toUpperCase() })} placeholder="24ABCDE1234F1Z5" />
              </div>
              <div>
                <label className={label} htmlFor="seller-phone">Phone</label>
                <input id="seller-phone" className={field} value={seller.phone} onChange={(e) => setSeller({ ...seller, phone: e.target.value })} placeholder="+91 98765 43210" />
              </div>
            </div>
            <div>
              <label className={label} htmlFor="seller-address">Address</label>
              <textarea id="seller-address" rows={2} className={field} value={seller.address} onChange={(e) => setSeller({ ...seller, address: e.target.value })} placeholder="Shop 4, Ring Road, Ahmedabad, Gujarat 380015" />
            </div>
            <div>
              <label className={label} htmlFor="seller-email">Email</label>
              <input id="seller-email" type="email" className={field} value={seller.email} onChange={(e) => setSeller({ ...seller, email: e.target.value })} placeholder="billing@yourbusiness.in" />
            </div>
          </section>

          <section className="space-y-3 rounded-lg border border-slate-200 p-4">
            <h2 className="font-semibold text-slate-900">Bill to</h2>
            <div>
              <label className={label} htmlFor="buyer-name">Client name</label>
              <input id="buyer-name" className={field} value={buyer.name} onChange={(e) => setBuyer({ ...buyer, name: e.target.value })} placeholder="Client Pvt Ltd" />
            </div>
            <div>
              <label className={label} htmlFor="buyer-gstin">Client GSTIN (optional)</label>
              <input id="buyer-gstin" className={field} value={buyer.gstin} onChange={(e) => setBuyer({ ...buyer, gstin: e.target.value.toUpperCase() })} />
            </div>
            <div>
              <label className={label} htmlFor="buyer-address">Client address</label>
              <textarea id="buyer-address" rows={2} className={field} value={buyer.address} onChange={(e) => setBuyer({ ...buyer, address: e.target.value })} />
            </div>
          </section>

          <section className="space-y-3 rounded-lg border border-slate-200 p-4">
            <h2 className="font-semibold text-slate-900">Invoice details</h2>
            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <label className={label} htmlFor="inv-number">Number</label>
                <input id="inv-number" className={field} value={meta.number} onChange={(e) => setMeta({ ...meta, number: e.target.value })} />
              </div>
              <div>
                <label className={label} htmlFor="inv-date">Date</label>
                <input id="inv-date" type="date" className={field} value={meta.date} onChange={(e) => setMeta({ ...meta, date: e.target.value })} />
              </div>
              <div>
                <label className={label} htmlFor="inv-due">Due date</label>
                <input id="inv-due" type="date" className={field} value={meta.due} onChange={(e) => setMeta({ ...meta, due: e.target.value })} />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className={label} htmlFor="gst-rate">GST rate (%)</label>
                <select id="gst-rate" className={field} value={gstRate} onChange={(e) => setGstRate(Number(e.target.value))}>
                  {[0, 5, 12, 18, 28].map((rate) => (
                    <option key={rate} value={rate}>{rate}%</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input type="checkbox" checked={sameState} onChange={(e) => setSameState(e.target.checked)} className="h-4 w-4" />
                  Client is in my state (CGST + SGST)
                </label>
              </div>
            </div>
          </section>

          <section className="space-y-3 rounded-lg border border-slate-200 p-4">
            <h2 className="font-semibold text-slate-900">Items</h2>
            {items.map((item, index) => (
              <div key={index} className="grid gap-2 sm:grid-cols-[1fr_5rem_7rem_2rem]">
                <input aria-label="Description" className={field} value={item.description} onChange={(e) => updateItem(index, { description: e.target.value })} placeholder="Website maintenance, September" />
                <input aria-label="Quantity" type="number" min={0} step="1" className={field} value={item.quantity} onChange={(e) => updateItem(index, { quantity: Number(e.target.value) })} />
                <input aria-label="Rate" type="number" min={0} step="0.01" className={field} value={item.rate} onChange={(e) => updateItem(index, { rate: Number(e.target.value) })} />
                <button type="button" aria-label={`Remove item ${index + 1}`} className="rounded-md border border-slate-300 text-slate-500 hover:bg-slate-50" onClick={() => setItems((c) => (c.length === 1 ? c : c.filter((_, i) => i !== index)))}>×</button>
              </div>
            ))}
            <button type="button" className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50" onClick={() => setItems((c) => [...c, { ...EMPTY_ITEM }])}>
              Add item
            </button>
            <div>
              <label className={label} htmlFor="inv-notes">Notes</label>
              <textarea id="inv-notes" rows={2} className={field} value={meta.notes} onChange={(e) => setMeta({ ...meta, notes: e.target.value })} />
            </div>
          </section>

          <button type="button" onClick={() => window.print()} className="w-full rounded-md bg-emerald-700 px-4 py-3 font-semibold text-white hover:bg-emerald-800">
            Save as PDF
          </button>
        </form>

        <section aria-label="Invoice preview" className="rounded-lg border border-slate-200 bg-white p-6 text-slate-900 print:border-0 print:p-0">
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4">
            <div>
              <h2 className="text-xl font-bold">{seller.name || "Your business name"}</h2>
              <p className="whitespace-pre-line text-sm text-slate-600">{seller.address || "Your address"}</p>
              <p className="text-sm text-slate-600">{[seller.phone, seller.email].filter(Boolean).join(" · ")}</p>
              {seller.gstin && <p className="text-sm text-slate-600">GSTIN: {seller.gstin}</p>}
            </div>
            <div className="text-right">
              <p className="text-lg font-semibold uppercase tracking-wide text-slate-500">Tax invoice</p>
              <p className="text-sm">No. {meta.number}</p>
              <p className="text-sm">Date: {meta.date}</p>
              <p className="text-sm">Due: {meta.due}</p>
            </div>
          </div>

          <div className="py-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Bill to</p>
            <p className="font-semibold">{buyer.name || "Client name"}</p>
            <p className="whitespace-pre-line text-sm text-slate-600">{buyer.address}</p>
            {buyer.gstin && <p className="text-sm text-slate-600">GSTIN: {buyer.gstin}</p>}
          </div>

          <table className="w-full border-t border-slate-200 text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2">Description</th>
                <th className="py-2 text-right">Qty</th>
                <th className="py-2 text-right">Rate</th>
                <th className="py-2 text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => (
                <tr key={index} className="border-t border-slate-100">
                  <td className="py-2">{item.description || "—"}</td>
                  <td className="py-2 text-right tabular-nums">{item.quantity}</td>
                  <td className="py-2 text-right tabular-nums">{inr(item.rate)}</td>
                  <td className="py-2 text-right tabular-nums">{inr(item.quantity * item.rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <dl className="mt-4 space-y-1 border-t border-slate-200 pt-4 text-sm">
            <div className="flex justify-between"><dt>Subtotal</dt><dd className="tabular-nums">{inr(totals.subtotal)}</dd></div>
            {sameState ? (
              <>
                <div className="flex justify-between text-slate-600"><dt>CGST {gstRate / 2}%</dt><dd className="tabular-nums">{inr(totals.half)}</dd></div>
                <div className="flex justify-between text-slate-600"><dt>SGST {gstRate / 2}%</dt><dd className="tabular-nums">{inr(totals.half)}</dd></div>
              </>
            ) : (
              <div className="flex justify-between text-slate-600"><dt>IGST {gstRate}%</dt><dd className="tabular-nums">{inr(totals.tax)}</dd></div>
            )}
            <div className="flex justify-between border-t border-slate-200 pt-2 text-base font-semibold"><dt>Total</dt><dd className="tabular-nums">{inr(totals.total)}</dd></div>
          </dl>

          {meta.notes && <p className="mt-4 whitespace-pre-line text-sm text-slate-600">{meta.notes}</p>}
          <p className="mt-6 text-xs text-slate-400">Made with Dhansetu Hub · dhansetuhub.in</p>
        </section>
      </div>

      <p className="mt-8 text-sm text-slate-500 print:hidden">
        This tool does the arithmetic and the layout. Check the GST treatment for your own business before sending an
        invoice; we are not tax advisers.
      </p>
    </main>
  );
}
