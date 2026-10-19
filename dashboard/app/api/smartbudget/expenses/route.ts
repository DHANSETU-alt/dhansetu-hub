/**
 * GET /api/smartbudget/expenses
 *
 * Returns recent expenses for the logged-in user
 *
 * Query Params:
 *   - limit: number (default: 20)
 *   - category: string (optional, filter by category)
 *
 * Security: Session validation required
 * Returns: Expense[] or 401 Unauthorized
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

    // Parse query params
    const url = new URL(req.url);
    const limit = parseInt(url.searchParams.get("limit") || "20", 10);
    const category = url.searchParams.get("category");

    // Generate user-specific mock data
    const mockData = generateUserMockData(session.user_id, session.user_email);

    // Filter by category if provided
    let expenses = mockData.expenses;
    if (category) {
      expenses = expenses.filter((e) => e.category === category);
    }

    // Sort by date (most recent first) and limit
    const filtered = expenses
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
      .slice(0, limit);

    return NextResponse.json(
      {
        success: true,
        data: filtered,
        meta: {
          userId: session.user_id,
          userEmail: session.user_email,
          month: mockData.month,
          total: mockData.totalExpenses,
          count: filtered.length,
        },
      },
      { status: 200 }
    );
  } catch (error) {
    console.error("[smartbudget/expenses] Error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
