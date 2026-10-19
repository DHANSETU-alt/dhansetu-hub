/**
 * GET /api/smartbudget/summary
 *
 * Returns complete SmartBudget summary for the logged-in user:
 * - Income sources
 * - Recent expenses
 * - Budget categories
 * - Financial summary (totals, net income, etc.)
 *
 * Security: Session validation required
 * Returns: SmartBudgetData or 401 Unauthorized
 */

import { NextRequest, NextResponse } from "next/server";
import { validateSession } from "@/lib/session-middleware";
import { generateUserMockData } from "@/lib/mock-data";

export async function GET(req: NextRequest) {
  try {
    // Validate session
    const session = await validateSession(req);
    if (!session) {
      return NextResponse.json(
        { error: "Unauthorized: Invalid or expired session" },
        { status: 401 }
      );
    }

    // Generate user-specific mock data
    const mockData = generateUserMockData(session.user_id, session.user_email);

    return NextResponse.json(
      {
        success: true,
        data: {
          ...mockData,
          // Add computed metrics
          savingsRate: mockData.totalIncome > 0 ? ((mockData.netIncome / mockData.totalIncome) * 100).toFixed(1) : "0",
          expenseRatio: mockData.totalIncome > 0 ? ((mockData.totalExpenses / mockData.totalIncome) * 100).toFixed(1) : "0",
        },
        meta: {
          userId: session.user_id,
          userEmail: session.user_email,
          fetchedAt: new Date().toISOString(),
          expiresAt: session.expires_at,
        },
      },
      { status: 200 }
    );
  } catch (error) {
    console.error("[smartbudget/summary] Error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
