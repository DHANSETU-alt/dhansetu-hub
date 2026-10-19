/**
 * GET /api/smartbudget/income
 *
 * Returns income sources for the logged-in user
 *
 * Security: Session validation required
 * Returns: IncomeSource[] or 401 Unauthorized
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
        data: mockData.incomeSources,
        meta: {
          userId: session.user_id,
          userEmail: session.user_email,
          month: mockData.month,
        },
      },
      { status: 200 }
    );
  } catch (error) {
    console.error("[smartbudget/income] Error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
