import { LeakShield, type Transaction } from '@/components/budget/LeakShield';
import { SmsParserToggle } from '@/components/budget/SmsParserToggle';
import { StatementImporter } from '@/components/budget/StatementImporter';

const sampleTransactions: Transaction[] = [
  { id: '1', amount: 499, date: '2026-09-10T08:00:00Z', merchant: 'Netflix' },
  { id: '2', amount: 499, date: '2026-09-10T14:00:00Z', merchant: 'Netflix' },
  { id: '3', amount: 1299, date: '2026-09-12T09:00:00Z', merchant: 'Amazon Prime' },
];

export default function SmartBudgetPage() {
  return (
    <main className="mx-auto max-w-2xl space-y-8 p-8">
      <h1 className="text-2xl font-bold text-slate-900">SmartBudget</h1>
      <p className="text-slate-600">Predictive expense management, powered by LeakShield v2.</p>
      <StatementImporter />
      <LeakShield transactions={sampleTransactions} inflationRate={0.06} />
      <SmsParserToggle />
    </main>
  );
}
