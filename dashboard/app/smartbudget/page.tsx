"use client";

/**
 * SmartBudget Dashboard
 *
 * Session-authenticated financial dashboard showing:
 * - Income sources
 * - Recent expenses
 * - Budget categories
 * - Financial summary
 *
 * Flow:
 * 1. Page loads, checks session validity
 * 2. If no session: redirect to login
 * 3. If session valid: fetch user-specific data
 * 4. Display widgets and tables
 * 5. Handle session timeout (5 min warning, auto-logout on expiry)
 */

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Card, CardHeader, CardBody, StatTile, EmptyState, Badge } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

interface IncomeSource {
  id: string;
  name: string;
  amount: number;
  frequency: "monthly" | "weekly" | "one-time";
  category: string;
}

interface Expense {
  id: string;
  name: string;
  amount: number;
  category: string;
  date: string;
}

interface BudgetCategory {
  id: string;
  name: string;
  allocated: number;
  spent: number;
}

interface SmartBudgetData {
  userId: number;
  userEmail: string;
  month: string;
  incomeSources: IncomeSource[];
  expenses: Expense[];
  budgetCategories: BudgetCategory[];
  totalIncome: number;
  totalExpenses: number;
  netIncome: number;
  savingsRate: string;
  expenseRatio: string;
}

type SessionStatus = "loading" | "authenticated" | "unauthenticated" | "expired";

function fmt(n: number): string {
  return `₹${n.toFixed(0)}`;
}

export default function SmartBudgetDashboard() {
  const router = useRouter();
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>("loading");
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [data, setData] = useState<SmartBudgetData | null>(null);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [dataError, setDataError] = useState<string | null>(null);
  const [isWarningVisible, setIsWarningVisible] = useState(false);

  // Format date for display
  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr + "T00:00:00");
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  // Check session validity via /api/auth/validate
  const checkSession = useCallback(async () => {
    try {
      const response = await fetch("/api/auth/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
        credentials: "include",
      });

      if (!response.ok) {
        console.warn("[SmartBudget] Session validation failed");
        setSessionStatus("unauthenticated");
        setSessionError("Session invalid or expired. Please login again.");
        // Redirect to login after a short delay
        setTimeout(() => {
          router.push("/auth-demo?redirect=/smartbudget");
        }, 2000);
        return false;
      }

      const sessionData = await response.json();
      setExpiresAt(sessionData.expires_at);
      setSessionStatus("authenticated");
      setSessionError(null);
      return true;
    } catch (error) {
      console.error("[SmartBudget] Session check error:", error);
      setSessionStatus("unauthenticated");
      setSessionError("Failed to verify session");
      return false;
    }
  }, [router]);

  // Fetch SmartBudget summary data
  const fetchSummary = useCallback(async () => {
    if (sessionStatus !== "authenticated") return;

    try {
      const response = await fetch("/api/smartbudget/summary", {
        credentials: "include",
      });

      if (!response.ok) {
        if (response.status === 401) {
          setSessionStatus("unauthenticated");
          setSessionError("Session expired. Please login again.");
          router.push("/auth-demo?redirect=/smartbudget");
          return;
        }
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      if (result.success && result.data) {
        setData(result.data);
        setDataError(null);
        // Update expires_at from metadata
        if (result.meta?.expiresAt) {
          setExpiresAt(result.meta.expiresAt);
        }
      }
    } catch (error) {
      console.error("[SmartBudget] Error fetching summary:", error);
      setDataError("Failed to load budget data");
    }
  }, [sessionStatus, router]);

  // Monitor session expiry
  useEffect(() => {
    if (!expiresAt) return;

    const checkExpiry = setInterval(() => {
      const now = new Date().getTime();
      const expiry = new Date(expiresAt).getTime();
      const timeUntilExpiry = expiry - now;

      // Show warning 5 minutes before expiry
      const warningTime = 5 * 60 * 1000;
      if (timeUntilExpiry <= warningTime && timeUntilExpiry > 0) {
        setIsWarningVisible(true);
      }

      // Auto-logout when expired
      if (timeUntilExpiry <= 0) {
        clearInterval(checkExpiry);
        setSessionStatus("expired");
        setSessionError("Session expired. Please login again.");
        // Hard refresh to clear all state
        setTimeout(() => {
          window.location.href = "/auth-demo?redirect=/smartbudget";
        }, 1500);
      }
    }, 30000); // Check every 30 seconds

    return () => clearInterval(checkExpiry);
  }, [expiresAt]);

  // Initial session check
  useEffect(() => {
    checkSession();
  }, [checkSession]);

  // Fetch data when session is authenticated
  useEffect(() => {
    if (sessionStatus === "authenticated") {
      fetchSummary();
    }
  }, [sessionStatus, fetchSummary]);

  // Loading state
  if (sessionStatus === "loading") {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="inline-block w-8 h-8 border-4 border-[var(--border)] border-t-[var(--ink)] rounded-full animate-spin mb-4"></div>
          <p className="text-[var(--muted-foreground)]">Verifying session...</p>
        </div>
      </div>
    );
  }

  // Unauthenticated state
  if (sessionStatus === "unauthenticated") {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card>
          <CardBody className="text-center">
            <div className="text-red-500 text-sm mb-4">
              ⚠️ {sessionError || "Please login to access SmartBudget"}
            </div>
            <p className="text-[var(--muted-foreground)] text-sm">Redirecting to login...</p>
          </CardBody>
        </Card>
      </div>
    );
  }

  // Session expired state
  if (sessionStatus === "expired") {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card>
          <CardBody className="text-center">
            <div className="text-red-500 text-sm mb-4">⚠️ {sessionError}</div>
            <p className="text-[var(--muted-foreground)] text-sm">Redirecting to login...</p>
          </CardBody>
        </Card>
      </div>
    );
  }

  // Main dashboard
  return (
    <div className="space-y-6">
      {/* Session expiry warning */}
      {isWarningVisible && (
        <div className="bg-[var(--warn-soft)] border-l-4 border-[var(--warn)] p-4 rounded-lg">
          <p className="text-sm text-[var(--warn)]">
            ⏰ Your session will expire in 5 minutes. Consider saving your work or click to refresh.
          </p>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">SmartBudget</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            {data?.userEmail ? `Logged in as ${data.userEmail}` : "Financial dashboard"}
          </p>
        </div>
        <AutoRefresh intervalSeconds={5} />
      </div>

      {/* Error state */}
      {dataError && (
        <div className="bg-red-500/10 border border-red-500/20 p-4 rounded-lg">
          <p className="text-sm text-red-600">{dataError}</p>
        </div>
      )}

      {/* Data loading */}
      {!data ? (
        <div className="text-center py-8">
          <div className="inline-block w-6 h-6 border-3 border-[var(--border)] border-t-[var(--ink)] rounded-full animate-spin mb-3"></div>
          <p className="text-[var(--muted-foreground)] text-sm">Loading your budget data...</p>
        </div>
      ) : (
        <>
          {/* Financial Summary Tiles */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatTile label="Total Income" value={fmt(data.totalIncome)} tone="good" />
            <StatTile label="Total Expenses" value={fmt(data.totalExpenses)} hint={`${data.expenseRatio}% of income`} />
            <StatTile
              label="Net Income"
              value={fmt(data.netIncome)}
              tone={data.netIncome >= 0 ? "good" : "bad"}
              hint={`${data.savingsRate}% savings rate`}
            />
            <StatTile label="Month" value={data.month} hint="Current budget period" />
          </div>

          {/* Income Sources */}
          <Card>
            <CardHeader title="Income Sources" subtitle={`${data.incomeSources.length} sources`} />
            <CardBody className="p-0">
              {data.incomeSources.length === 0 ? (
                <EmptyState>No income sources recorded</EmptyState>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--muted-foreground)] border-b border-[var(--border)]">
                      <th className="px-5 py-2 font-medium">Source</th>
                      <th className="px-5 py-2 font-medium">Amount</th>
                      <th className="px-5 py-2 font-medium">Frequency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.incomeSources.map((source) => (
                      <tr key={source.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--surface-2)]">
                        <td className="px-5 py-2">{source.name}</td>
                        <td className="px-5 py-2 font-mono-num font-semibold">{fmt(source.amount)}</td>
                        <td className="px-5 py-2">
                          <Badge tone="neutral">{source.frequency}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardBody>
          </Card>

          {/* Recent Expenses */}
          <Card>
            <CardHeader title="Recent Expenses" subtitle={`Last ${data.expenses.length} transactions`} />
            <CardBody className="p-0">
              {data.expenses.length === 0 ? (
                <EmptyState>No expenses recorded</EmptyState>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--muted-foreground)] border-b border-[var(--border)]">
                      <th className="px-5 py-2 font-medium">Description</th>
                      <th className="px-5 py-2 font-medium">Category</th>
                      <th className="px-5 py-2 font-medium">Amount</th>
                      <th className="px-5 py-2 font-medium">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.expenses.slice(0, 10).map((expense) => (
                      <tr key={expense.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--surface-2)]">
                        <td className="px-5 py-2">{expense.name}</td>
                        <td className="px-5 py-2">
                          <Badge tone="neutral">{expense.category}</Badge>
                        </td>
                        <td className="px-5 py-2 font-mono-num">{fmt(expense.amount)}</td>
                        <td className="px-5 py-2 text-[var(--muted-foreground)] text-xs">{formatDate(expense.date)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardBody>
          </Card>

          {/* Budget Categories */}
          <Card>
            <CardHeader title="Budget by Category" subtitle="Allocated vs. Spent" />
            <CardBody className="p-0">
              {data.budgetCategories.length === 0 ? (
                <EmptyState>No budget categories</EmptyState>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--muted-foreground)] border-b border-[var(--border)]">
                      <th className="px-5 py-2 font-medium">Category</th>
                      <th className="px-5 py-2 font-medium">Allocated</th>
                      <th className="px-5 py-2 font-medium">Spent</th>
                      <th className="px-5 py-2 font-medium">Remaining</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.budgetCategories.map((budget) => {
                      const remaining = budget.allocated - budget.spent;
                      const percentUsed = ((budget.spent / budget.allocated) * 100).toFixed(0);
                      return (
                        <tr key={budget.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--surface-2)]">
                          <td className="px-5 py-2">{budget.name}</td>
                          <td className="px-5 py-2 font-mono-num">{fmt(budget.allocated)}</td>
                          <td className="px-5 py-2 font-mono-num">{fmt(budget.spent)}</td>
                          <td className="px-5 py-2 font-mono-num">
                            <span style={{ color: remaining >= 0 ? "var(--good)" : "var(--bad)" }}>
                              {fmt(remaining)} ({percentUsed}%)
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </CardBody>
          </Card>
        </>
      )}
    </div>
  );
}
