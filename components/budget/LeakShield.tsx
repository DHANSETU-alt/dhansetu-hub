'use client';

export interface Transaction {
  id: string;
  amount: number;
  date: string; // ISO 8601
  merchant: string;
}

interface LeakShieldProps {
  transactions: Transaction[];
  inflationRate?: number;
}

interface DuplicateGroup {
  merchant: string;
  amount: number;
  transactions: Transaction[];
}

const DAY_MS = 24 * 60 * 60 * 1000;

function detectDuplicates(txs: Transaction[]): DuplicateGroup[] {
  const sorted = [...txs].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  const groups = new Map<string, Transaction[]>();

  for (const tx of sorted) {
    const key = `${tx.merchant}:${tx.amount}`;
    const bucket = groups.get(key) ?? [];
    const withinWindow = bucket.filter(
      (prior) => new Date(tx.date).getTime() - new Date(prior.date).getTime() <= DAY_MS,
    );
    groups.set(key, [...withinWindow, tx]);
  }

  return Array.from(groups.entries())
    .filter(([, txs]) => txs.length > 1)
    .map(([, txs]) => ({
      merchant: txs[0].merchant,
      amount: txs[0].amount,
      transactions: txs,
    }));
}

function Alert({ icon, title, detail }: { icon: string; title: string; detail: string }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-amber-300 bg-amber-50 p-3">
      <span aria-hidden className="text-xl leading-none">{icon}</span>
      <div>
        <p className="font-semibold text-amber-900">{title}</p>
        <p className="text-sm text-amber-800">{detail}</p>
      </div>
    </div>
  );
}

export function LeakShield({ transactions, inflationRate = 0.06 }: LeakShieldProps) {
  const duplicates = detectDuplicates(transactions);
  const leakedAmount = duplicates.reduce(
    (sum, group) => sum + group.amount * (group.transactions.length - 1),
    0,
  );

  return (
    <section aria-labelledby="leakshield-heading" className="space-y-3">
      <h3 id="leakshield-heading" className="font-semibold text-slate-900">LeakShield v2 Active</h3>

      <Alert
        icon="⚡"
        title="Inflation Alert"
        detail={`Your recurring costs rose ${(inflationRate * 100).toFixed(0)}% this year.`}
      />

      {duplicates.length > 0 && (
        <Alert
          icon="🔁"
          title={`${duplicates.length} possible duplicate charge${duplicates.length > 1 ? 's' : ''} found`}
          detail={`₹${leakedAmount.toLocaleString('en-IN')} in same-amount charges from the same merchant within 24 hours.`}
        />
      )}

      {duplicates.length === 0 && (
        <p className="text-sm text-slate-500">No duplicate charges detected in this period.</p>
      )}
    </section>
  );
}
