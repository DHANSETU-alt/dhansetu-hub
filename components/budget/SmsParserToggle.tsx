'use client';

import { useState } from 'react';

export interface ParsedSms {
  bank: 'UPI' | 'HDFC' | 'ICICI' | 'SBI' | 'Axis' | 'Unknown';
  type: 'debited' | 'credited';
  amount: number;
  account?: string;
}

// All parsing happens in the browser. Raw SMS text is never sent to any server.
const PATTERNS: { bank: ParsedSms['bank']; regex: RegExp }[] = [
  { bank: 'UPI', regex: /VPA\s([\w.@]+)\s(debited|credited)\sby\sINR\s([\d,.]+)/i },
  { bank: 'HDFC', regex: /HDFC Bank:.*A\/c\s.*X(\d{4})\s(debited|credited)\sfor\sRs\s([\d,.]+)/i },
  { bank: 'ICICI', regex: /ICICI Bank Acct\sXX(\d{3})\s(debited|credited).*Rs\s([\d,.]+)/i },
  { bank: 'SBI', regex: /Your A\/c\s.*X(\d{4})\s(debited|credited)\sby\sRs\.?\s?([\d,.]+)/i },
  { bank: 'Axis', regex: /Axis Bank.*A\/c\s.*X(\d{4})\s(debited|credited).*INR\s([\d,.]+)/i },
];

export function parseIndianSMS(text: string): ParsedSms | null {
  for (const { bank, regex } of PATTERNS) {
    const match = text.match(regex);
    if (!match) continue;
    const [, account, type, amountRaw] = match;
    return {
      bank,
      account,
      type: type.toLowerCase() as ParsedSms['type'],
      amount: Number(amountRaw.replace(/,/g, '')),
    };
  }
  return null;
}

export function SmsParserToggle() {
  const [enabled, setEnabled] = useState(false);
  const [text, setText] = useState('');
  const [result, setResult] = useState<ParsedSms | null>(null);

  return (
    <div className="space-y-3">
      <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
        />
        Enable on-device SMS parsing (nothing leaves your browser)
      </label>

      {enabled && (
        <div className="space-y-2">
          <textarea
            className="w-full rounded-md border border-slate-300 p-2 text-sm"
            rows={3}
            placeholder="Paste a bank/UPI SMS to test parsing locally"
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              setResult(parseIndianSMS(e.target.value));
            }}
          />
          {result ? (
            <p className="text-sm text-emerald-700">
              Parsed: {result.bank} · ₹{result.amount.toLocaleString('en-IN')} {result.type}
            </p>
          ) : text ? (
            <p className="text-sm text-slate-500">No supported bank/UPI pattern recognized yet.</p>
          ) : null}
        </div>
      )}
    </div>
  );
}
