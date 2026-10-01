"use client";

import { useState } from "react";
import { Card, CardHeader, CardBody, StatTile } from "@/components/ui";

interface TaxResult {
  old_regime: {
    gross_income: number;
    taxable_income: number;
    total_tax: number;
    cess: number;
    total_liability: number;
  };
  new_regime: {
    gross_income: number;
    taxable_income: number;
    total_tax: number;
    cess: number;
    total_liability: number;
    is_rebate_eligible: boolean;
    rebate_amount: number;
  };
  recommendation: string;
  tax_savings: number;
}

interface GSTResult {
  total_expenses: number;
  total_gst_liability: number;
  total_gst_reported: number;
  total_leak: number;
  compliance_score: number;
  risk_level: string;
  findings: Array<{
    category: string;
    description: string;
    expense_amount: number;
    expected_gst_rate: string;
    expected_gst_liability: number;
    gst_reported: number;
    leak_amount: number;
    is_input_credit_eligible: boolean;
    recommendation: string;
  }>;
  recommendations: string[];
}

const DEDUCTION_CATEGORIES = {
  "80C": "Life Insurance, PPF, Mutual Funds, Education (Max ₹150,000)",
  "80D": "Medical Insurance Premium (Max ₹100,000)",
  "80D_parents": "Medical Insurance for Parents 60+ (Max ₹50,000)",
  "80CCD": "Pension Contribution CCS (Max ₹50,000)",
  "80E": "Education Loan Interest (Unlimited)",
  "80EE": "Home Loan Interest First-time Buyers (Max ₹200,000)",
  "80EEA": "EV Purchase Loan Interest (Max ₹500,000)",
};

const GST_CATEGORIES = [
  "office_supplies",
  "software",
  "professional_fees",
  "internet_telecom",
  "electricity",
  "travel",
  "general_services",
  "restaurant",
];

export default function TaxEstimatorPage() {
  const [activeTab, setActiveTab] = useState<"tax" | "gst">("tax");

  // Tax Estimator State
  const [grossIncome, setGrossIncome] = useState<string>("500000");
  const [deductions, setDeductions] = useState<{ category: string; description: string; amount: number }[]>([]);
  const [newDeductionCategory, setNewDeductionCategory] = useState("80C");
  const [newDeductionAmount, setNewDeductionAmount] = useState("");
  const [taxResult, setTaxResult] = useState<TaxResult | null>(null);
  const [taxLoading, setTaxLoading] = useState(false);

  // GST Audit State
  const [gstExpenses, setGstExpenses] = useState<
    { category: string; description: string; amount: number; has_gst_invoice: boolean; gst_paid: number }[]
  >([]);
  const [newExpenseCategory, setNewExpenseCategory] = useState("office_supplies");
  const [newExpenseDesc, setNewExpenseDesc] = useState("");
  const [newExpenseAmount, setNewExpenseAmount] = useState("");
  const [newExpenseGst, setNewExpenseGst] = useState("");
  const [newExpenseInvoice, setNewExpenseInvoice] = useState(true);
  const [gstResult, setGstResult] = useState<GSTResult | null>(null);
  const [gstLoading, setGstLoading] = useState(false);

  // Tax Estimator Functions
  const addDeduction = () => {
    if (newDeductionAmount && !isNaN(Number(newDeductionAmount))) {
      setDeductions([
        ...deductions,
        {
          category: newDeductionCategory,
          description: DEDUCTION_CATEGORIES[newDeductionCategory as keyof typeof DEDUCTION_CATEGORIES],
          amount: Number(newDeductionAmount),
        },
      ]);
      setNewDeductionAmount("");
    }
  };

  const removeDeduction = (index: number) => {
    setDeductions(deductions.filter((_, i) => i !== index));
  };

  const calculateTax = async () => {
    if (!grossIncome || isNaN(Number(grossIncome))) {
      alert("Please enter a valid income");
      return;
    }

    setTaxLoading(true);
    try {
      const params = new URLSearchParams({
        income: grossIncome,
        deductions: JSON.stringify(deductions),
      });

      const response = await fetch(`/api/tax/calculate?${params}`);
      const data = await response.json();
      setTaxResult(data);
    } catch (error) {
      console.error("Tax calculation error:", error);
      alert("Failed to calculate tax");
    } finally {
      setTaxLoading(false);
    }
  };

  // GST Audit Functions
  const addExpense = () => {
    if (newExpenseDesc && newExpenseAmount && !isNaN(Number(newExpenseAmount))) {
      const gstPaid = newExpenseGst ? Number(newExpenseGst) : 0;
      setGstExpenses([
        ...gstExpenses,
        {
          category: newExpenseCategory,
          description: newExpenseDesc,
          amount: Number(newExpenseAmount),
          has_gst_invoice: newExpenseInvoice,
          gst_paid: gstPaid,
        },
      ]);
      setNewExpenseDesc("");
      setNewExpenseAmount("");
      setNewExpenseGst("");
      setNewExpenseInvoice(true);
    }
  };

  const removeExpense = (index: number) => {
    setGstExpenses(gstExpenses.filter((_, i) => i !== index));
  };

  const analyzeGst = async () => {
    if (gstExpenses.length === 0) {
      alert("Please add at least one expense");
      return;
    }

    setGstLoading(true);
    try {
      const params = new URLSearchParams({
        expenses: JSON.stringify(gstExpenses),
      });

      const response = await fetch(`/api/tax/gst-audit?${params}`);
      const data = await response.json();
      setGstResult(data);
    } catch (error) {
      console.error("GST audit error:", error);
      alert("Failed to analyze GST");
    } finally {
      setGstLoading(false);
    }
  };

  const fmt = (n: number) => {
    return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
  };

  const fmtPct = (n: number) => {
    return `${n.toFixed(1)}%`;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Indian Tax Estimator & GST LeakShield</h1>
        <p className="text-sm text-[var(--muted-foreground)] mt-1">
          Calculate income tax (old vs new regime) and analyze GST compliance for business expenses.
        </p>
      </div>

      {/* Tab Selector */}
      <div className="flex gap-2 border-b border-[var(--border)]">
        <button
          onClick={() => setActiveTab("tax")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
            activeTab === "tax"
              ? "border-[var(--accent)] text-[var(--accent)]"
              : "border-transparent text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
          }`}
        >
          Tax Calculator
        </button>
        <button
          onClick={() => setActiveTab("gst")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
            activeTab === "gst"
              ? "border-[var(--accent)] text-[var(--accent)]"
              : "border-transparent text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
          }`}
        >
          GST Audit
        </button>
      </div>

      {/* Tax Calculator Tab */}
      {activeTab === "tax" && (
        <div className="space-y-6">
          <Card>
            <CardHeader title="Income & Deductions" />
            <CardBody className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Gross Annual Income (₹)</label>
                <input
                  type="number"
                  value={grossIncome}
                  onChange={(e) => setGrossIncome(e.target.value)}
                  className="w-full px-3 py-2 border border-[var(--border)] rounded text-sm"
                  placeholder="500000"
                />
              </div>

              <div className="bg-[var(--muted)] p-4 rounded text-sm">
                <p className="font-semibold mb-2">Add Deductions (Optional)</p>
                <div className="space-y-2">
                  <div className="grid grid-cols-3 gap-2">
                    <select
                      value={newDeductionCategory}
                      onChange={(e) => setNewDeductionCategory(e.target.value)}
                      className="px-3 py-2 border border-[var(--border)] rounded text-sm"
                    >
                      {Object.entries(DEDUCTION_CATEGORIES).map(([key, desc]) => (
                        <option key={key} value={key}>
                          {key}
                        </option>
                      ))}
                    </select>
                    <input
                      type="number"
                      value={newDeductionAmount}
                      onChange={(e) => setNewDeductionAmount(e.target.value)}
                      placeholder="Amount"
                      className="px-3 py-2 border border-[var(--border)] rounded text-sm"
                    />
                    <button
                      onClick={addDeduction}
                      className="px-3 py-2 bg-[var(--accent)] text-[var(--accent-foreground)] rounded text-sm font-medium hover:opacity-90"
                    >
                      Add
                    </button>
                  </div>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    {DEDUCTION_CATEGORIES[newDeductionCategory as keyof typeof DEDUCTION_CATEGORIES]}
                  </p>
                </div>
              </div>

              {deductions.length > 0 && (
                <div>
                  <p className="text-sm font-semibold mb-2">Added Deductions</p>
                  <div className="space-y-2">
                    {deductions.map((d, i) => (
                      <div key={i} className="flex items-center justify-between bg-[var(--muted)] p-2 rounded text-sm">
                        <div>
                          <p className="font-medium">{d.category}</p>
                          <p className="text-xs text-[var(--muted-foreground)]">{fmt(d.amount)}</p>
                        </div>
                        <button
                          onClick={() => removeDeduction(i)}
                          className="text-red-500 hover:text-red-700 text-sm"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <button
                onClick={calculateTax}
                disabled={taxLoading}
                className="w-full px-4 py-2 bg-[var(--accent)] text-[var(--accent-foreground)] rounded font-medium hover:opacity-90 disabled:opacity-50"
              >
                {taxLoading ? "Calculating..." : "Calculate Tax"}
              </button>
            </CardBody>
          </Card>

          {/* Tax Results */}
          {taxResult && (
            <>
              <Card>
                <CardHeader title="Recommendation" />
                <CardBody>
                  <div className="bg-[var(--muted)] p-6 rounded">
                    <p className="text-sm text-[var(--muted-foreground)] mb-2">Recommended Regime</p>
                    <p className="text-3xl font-bold uppercase tracking-wide text-[var(--accent)]">
                      {taxResult.recommendation} Regime
                    </p>
                    <p className="text-sm mt-4">
                      Tax Savings: <span className="font-semibold text-[var(--good)]">{fmt(taxResult.tax_savings)}</span>
                    </p>
                  </div>
                </CardBody>
              </Card>

              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardHeader title="Old Regime" subtitle="With Standard Deduction + Deductions" />
                  <CardBody className="space-y-4">
                    <div>
                      <p className="text-xs text-[var(--muted-foreground)] uppercase">Gross Income</p>
                      <p className="text-xl font-semibold">{fmt(taxResult.old_regime.gross_income)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--muted-foreground)] uppercase">Taxable Income</p>
                      <p className="text-xl font-semibold">{fmt(taxResult.old_regime.taxable_income)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--muted-foreground)] uppercase">Tax</p>
                      <p className="text-lg font-semibold">{fmt(taxResult.old_regime.total_tax)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--muted-foreground)] uppercase">Cess (4%)</p>
                      <p className="text-lg font-semibold">{fmt(taxResult.old_regime.cess)}</p>
                    </div>
                    <div className="pt-4 border-t border-[var(--border)]">
                      <p className="text-xs text-[var(--muted-foreground)] uppercase">Total Liability</p>
                      <p className="text-2xl font-bold text-[var(--foreground)]">
                        {fmt(taxResult.old_regime.total_liability)}
                      </p>
                    </div>
                  </CardBody>
                </Card>

                <Card>
                  <CardHeader title="New Regime" subtitle="With Standard Deduction Only (Section 87A)" />
                  <CardBody className="space-y-4">
                    <div>
                      <p className="text-xs text-[var(--muted-foreground)] uppercase">Gross Income</p>
                      <p className="text-xl font-semibold">{fmt(taxResult.new_regime.gross_income)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--muted-foreground)] uppercase">Taxable Income</p>
                      <p className="text-xl font-semibold">{fmt(taxResult.new_regime.taxable_income)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--muted-foreground)] uppercase">Tax</p>
                      <p className="text-lg font-semibold">{fmt(taxResult.new_regime.total_tax)}</p>
                    </div>
                    {taxResult.new_regime.is_rebate_eligible && (
                      <div>
                        <p className="text-xs text-[var(--muted-foreground)] uppercase">Section 87A Rebate</p>
                        <p className="text-lg font-semibold text-[var(--good)]">
                          -{fmt(taxResult.new_regime.rebate_amount)}
                        </p>
                      </div>
                    )}
                    <div>
                      <p className="text-xs text-[var(--muted-foreground)] uppercase">Cess (4%)</p>
                      <p className="text-lg font-semibold">{fmt(taxResult.new_regime.cess)}</p>
                    </div>
                    <div className="pt-4 border-t border-[var(--border)]">
                      <p className="text-xs text-[var(--muted-foreground)] uppercase">Total Liability</p>
                      <p className="text-2xl font-bold text-[var(--foreground)]">
                        {fmt(taxResult.new_regime.total_liability)}
                      </p>
                    </div>
                  </CardBody>
                </Card>
              </div>
            </>
          )}
        </div>
      )}

      {/* GST Audit Tab */}
      {activeTab === "gst" && (
        <div className="space-y-6">
          <Card>
            <CardHeader title="Add Expenses" />
            <CardBody className="space-y-4">
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Category</label>
                  <select
                    value={newExpenseCategory}
                    onChange={(e) => setNewExpenseCategory(e.target.value)}
                    className="w-full px-3 py-2 border border-[var(--border)] rounded text-sm"
                  >
                    {GST_CATEGORIES.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Description</label>
                  <input
                    type="text"
                    value={newExpenseDesc}
                    onChange={(e) => setNewExpenseDesc(e.target.value)}
                    placeholder="e.g., SaaS subscription annual"
                    className="w-full px-3 py-2 border border-[var(--border)] rounded text-sm"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-sm font-medium mb-2">Expense Amount (₹)</label>
                    <input
                      type="number"
                      value={newExpenseAmount}
                      onChange={(e) => setNewExpenseAmount(e.target.value)}
                      placeholder="120000"
                      className="w-full px-3 py-2 border border-[var(--border)] rounded text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">GST Paid (₹)</label>
                    <input
                      type="number"
                      value={newExpenseGst}
                      onChange={(e) => setNewExpenseGst(e.target.value)}
                      placeholder="14400"
                      className="w-full px-3 py-2 border border-[var(--border)] rounded text-sm"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={newExpenseInvoice}
                    onChange={(e) => setNewExpenseInvoice(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <label className="text-sm">Has proper GST invoice</label>
                </div>

                <button
                  onClick={addExpense}
                  className="px-4 py-2 bg-[var(--accent)] text-[var(--accent-foreground)] rounded text-sm font-medium hover:opacity-90"
                >
                  Add Expense
                </button>
              </div>
            </CardBody>
          </Card>

          {gstExpenses.length > 0 && (
            <Card>
              <CardHeader title="Added Expenses" subtitle={`${gstExpenses.length} expense(s)`} />
              <CardBody>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {gstExpenses.map((e, i) => (
                    <div key={i} className="flex items-center justify-between bg-[var(--muted)] p-3 rounded text-sm">
                      <div>
                        <p className="font-medium">{e.description}</p>
                        <p className="text-xs text-[var(--muted-foreground)]">
                          {e.category} • {fmt(e.amount)} {e.has_gst_invoice ? "✓" : "✗"}
                        </p>
                      </div>
                      <button
                        onClick={() => removeExpense(i)}
                        className="text-red-500 hover:text-red-700 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>

                <button
                  onClick={analyzeGst}
                  disabled={gstLoading}
                  className="w-full mt-4 px-4 py-2 bg-[var(--accent)] text-[var(--accent-foreground)] rounded font-medium hover:opacity-90 disabled:opacity-50"
                >
                  {gstLoading ? "Analyzing..." : "Analyze GST Compliance"}
                </button>
              </CardBody>
            </Card>
          )}

          {/* GST Results */}
          {gstResult && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatTile
                  label="Total Expenses"
                  value={fmt(gstResult.total_expenses)}
                  tone="info"
                />
                <StatTile
                  label="GST Liability"
                  value={fmt(gstResult.total_gst_liability)}
                  tone="info"
                />
                <StatTile
                  label="GST Reported"
                  value={fmt(gstResult.total_gst_reported)}
                  tone={gstResult.total_leak > 0 ? "bad" : "good"}
                />
                <StatTile
                  label="GST Leak"
                  value={fmt(gstResult.total_leak)}
                  tone={gstResult.total_leak > 0 ? "bad" : "good"}
                />
              </div>

              <Card>
                <CardHeader
                  title="Compliance Score"
                  subtitle={`Risk Level: ${gstResult.risk_level.toUpperCase()}`}
                />
                <CardBody>
                  <div className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-sm font-medium">Compliance</p>
                        <p className="text-lg font-bold">{fmtPct(gstResult.compliance_score)}</p>
                      </div>
                      <div className="w-full bg-[var(--muted)] rounded-full h-2">
                        <div
                          className="bg-[var(--accent)] h-2 rounded-full"
                          style={{
                            width: `${gstResult.compliance_score}%`,
                          }}
                        />
                      </div>
                    </div>

                    {gstResult.recommendations.length > 0 && (
                      <div className="pt-4 border-t border-[var(--border)]">
                        <p className="text-sm font-semibold mb-2">Recommendations</p>
                        <ul className="space-y-1 text-sm">
                          {gstResult.recommendations.map((rec, i) => (
                            <li key={i} className="text-[var(--muted-foreground)]">
                              • {rec}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </CardBody>
              </Card>

              {gstResult.findings.length > 0 && (
                <Card>
                  <CardHeader title="GST Compliance Issues" subtitle={`${gstResult.findings.length} finding(s)`} />
                  <CardBody>
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {gstResult.findings.map((f, i) => (
                        <div key={i} className="border border-[var(--border)] rounded p-3">
                          <div className="flex items-start justify-between mb-2">
                            <div>
                              <p className="font-semibold text-sm">{f.description}</p>
                              <p className="text-xs text-[var(--muted-foreground)]">
                                Category: {f.category}
                              </p>
                            </div>
                            {f.leak_amount > 0 && (
                              <div className="text-right">
                                <p className="text-sm font-semibold text-red-500">
                                  Leak: {fmt(f.leak_amount)}
                                </p>
                              </div>
                            )}
                          </div>
                          <div className="grid grid-cols-3 gap-2 text-xs mb-2 py-2 bg-[var(--muted)] px-2 rounded">
                            <div>
                              <p className="text-[var(--muted-foreground)]">Expense</p>
                              <p className="font-mono">{fmt(f.expense_amount)}</p>
                            </div>
                            <div>
                              <p className="text-[var(--muted-foreground)]">Expected GST</p>
                              <p className="font-mono">{fmt(f.expected_gst_liability)}</p>
                            </div>
                            <div>
                              <p className="text-[var(--muted-foreground)]">Reported</p>
                              <p className="font-mono">{fmt(f.gst_reported)}</p>
                            </div>
                          </div>
                          <p className="text-xs text-[var(--muted-foreground)]">{f.recommendation}</p>
                        </div>
                      ))}
                    </div>
                  </CardBody>
                </Card>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
