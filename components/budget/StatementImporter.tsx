'use client';

import { useState } from 'react';
import { LeakShield, type Transaction } from './LeakShield';

function splitRow(row: string, delimiter: string) {
  const cells: string[] = [];
  let cell = '';
  let quoted = false;
  for (let i = 0; i < row.length; i += 1) {
    const char = row[i];
    if (char === '"' && row[i + 1] === '"') { cell += '"'; i += 1; continue; }
    if (char === '"') { quoted = !quoted; continue; }
    if (char === delimiter && !quoted) { cells.push(cell.trim()); cell = ''; continue; }
    cell += char;
  }
  cells.push(cell.trim());
  return cells;
}

function parseAmount(value: string) {
  const normalized = value.replace(/[₹,\s]/g, '').replace(/[()]/g, '-');
  const amount = Number(normalized);
  return Number.isFinite(amount) ? amount : 0;
}

export function parseStatement(text: string): Transaction[] {
  const rows = text.split(/\r?\n/).map((row) => row.trim()).filter(Boolean);
  if (rows.length < 2) return [];
  const delimiter = rows[0].includes('\t') ? '\t' : ',';
  const headers = splitRow(rows[0], delimiter).map((header) => header.toLowerCase().replace(/[^a-z]/g, ''));
  const find = (...names: string[]) => headers.findIndex((header) => names.includes(header));
  const dateIndex = find('date', 'transactiondate', 'valuedate');
  const merchantIndex = find('description', 'narration', 'merchant', 'particulars', 'remarks');
  const amountIndex = find('amount', 'transactionamount', 'debitamount');
  const debitIndex = find('debit', 'withdrawal', 'debitamount');
  if (dateIndex < 0 || merchantIndex < 0 || (amountIndex < 0 && debitIndex < 0)) return [];

  return rows.slice(1).flatMap((row, index) => {
    const cells = splitRow(row, delimiter);
    const amount = parseAmount(cells[debitIndex >= 0 ? debitIndex : amountIndex] ?? '');
    const dateRaw = cells[dateIndex] ?? '';
    const date = new Date(dateRaw);
    if (!amount || Number.isNaN(date.getTime())) return [];
    return [{ id: `import-${index}`, amount: Math.abs(amount), date: date.toISOString(), merchant: cells[merchantIndex] || 'Unknown merchant' }];
  });
}

export function StatementImporter() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [message, setMessage] = useState('No statement loaded.');

  async function onFile(file?: File) {
    if (!file) return;
    if (!/\.(csv|tsv|txt)$/i.test(file.name)) {
      setMessage('For safety, this MVP accepts CSV/TSV exports only. Never enter a bank password here.');
      return;
    }
    const parsed = parseStatement(await file.text());
    setTransactions(parsed);
    setMessage(parsed.length ? `${parsed.length} debit transactions imported locally. Nothing was uploaded.` : 'No supported debit rows found. Export Date, Description, and Debit/Amount columns.');
  }

  return <section className="space-y-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-5"><div><h2 className="font-semibold text-emerald-950">Import bank statement</h2><p className="mt-1 text-sm text-emerald-800">Upload a CSV/TSV export to auto-adjust LeakShield in this browser.</p></div><label className="block cursor-pointer rounded-xl border-2 border-dashed border-emerald-400 bg-white p-5 text-center text-sm font-semibold text-emerald-900"><span>Choose CSV or TSV statement</span><input className="sr-only" type="file" accept=".csv,.tsv,.txt,text/csv,text/tab-separated-values" onChange={(event) => void onFile(event.target.files?.[0])} /></label><p className="text-xs text-emerald-800" aria-live="polite">{message}</p><p className="text-xs text-slate-600">Privacy: processing is local and memory-only. DhanSetu never receives your statement or bank password. Password-protected PDF import is deliberately not enabled until local decryption is independently tested.</p>{transactions.length > 0 && <LeakShield transactions={transactions} />}</section>;
}
