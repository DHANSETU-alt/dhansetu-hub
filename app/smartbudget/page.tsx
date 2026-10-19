import { BudgetWorkspace } from '@/components/budget/BudgetWorkspace';
import { SmsParserToggle } from '@/components/budget/SmsParserToggle';

export default function SmartBudgetPage() {
  return (
    <main className="mx-auto min-h-screen max-w-6xl space-y-8 bg-slate-50 px-5 py-10 sm:px-8">
      <h1 className="text-2xl font-bold text-slate-900">SmartBudget</h1>
      <p className="max-w-2xl text-slate-600">A private-first money workspace for income, commitments, savings, and explainable leak checks. Your current data stays in this browser.</p>
      <BudgetWorkspace />
      <SmsParserToggle />
    </main>
  );
}
