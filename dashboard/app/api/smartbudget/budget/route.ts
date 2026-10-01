/**
 * GET /api/smartbudget/budget
 *
 * Returns budget categories and allocation for the logged-in user
 *
 * Security: Session validation required
 * Returns: BudgetCategory[] or 401 Unauthorized
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
        data: mockData.budgetCategories,
        meta: {
          userId: session.user_id,
          userEmail: session.user_email,
          month: mockData.month,
          totalAllocated: mockData.budgetCategories.reduce((sum, b) => sum + b.allocated, 0),
          totalSpent: mockData.budgetCategories.reduce((sum, b) => sum + b.spent, 0),
        },
      },
      { status: 200 }
    );
  } catch (error) {
    console.error("[smartbudget/budget] Error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
