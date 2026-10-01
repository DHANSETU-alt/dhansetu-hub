/**
 * GET /api/peopledesk/tickets
 *
 * List support tickets with filtering
 *
 * Query parameters:
 * - status: "open" | "in-progress" | "resolved" (optional)
 * - priority: "high" | "medium" | "low" (optional)
 * - limit: number (default 50)
 * - role: "customer" | "support" (default "customer") - determines which tickets to show
 *
 * Returns: Array of ticket objects
 */

import { NextRequest, NextResponse } from "next/server";
import { validateSession } from "@/lib/session-middleware";

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

    const { searchParams } = new URL(req.url);
    const status = searchParams.get("status");
    const priority = searchParams.get("priority");
    const limit = parseInt(searchParams.get("limit") || "50", 10);
    const role = searchParams.get("role") || "customer";

    // Validate parameters
    if (status && !["open", "in-progress", "resolved"].includes(status)) {
      return NextResponse.json(
        { error: "Invalid status filter" },
        { status: 400 }
      );
    }

    if (priority && !["high", "medium", "low"].includes(priority)) {
      return NextResponse.json(
        { error: "Invalid priority filter" },
        { status: 400 }
      );
    }

    if (limit > 1000) {
      return NextResponse.json(
        { error: "Limit cannot exceed 1000" },
        { status: 400 }
      );
    }

    // Generate mock tickets based on role
    const mockTickets = generateMockTickets(session.user_id, role, status, priority, limit);

    return NextResponse.json(
      {
        success: true,
        data: mockTickets,
        meta: {
          userId: session.user_id,
          role,
          totalCount: mockTickets.length,
          filters: { status, priority },
          fetchedAt: new Date().toISOString(),
        },
      },
      { status: 200 }
    );
  } catch (error) {
    console.error("[peopledesk/tickets] Error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

function generateMockTickets(
  userId: string,
  role: string,
  statusFilter?: string | null,
  priorityFilter?: string | null,
  limit: number = 50
): any[] {
  const mockTicketData = [
    {
      id: "ticket_001_cust_abc",
      customer_id: userId,
      subject: "Payment processing error on checkout",
      description: "Getting an error when trying to complete payment",
      priority: "high",
      status: "open",
      assigned_to: null,
      created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      resolved_at: null,
      first_response_at: null,
    },
    {
      id: "ticket_002_cust_abc",
      customer_id: userId,
      subject: "How to export data from dashboard",
      description: "Need help understanding how to export my data",
      priority: "medium",
      status: "in-progress",
      assigned_to: "agent_001",
      created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
      resolved_at: null,
      first_response_at: new Date(Date.now() - 22 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: "ticket_003_cust_abc",
      customer_id: userId,
      subject: "Feature request: dark mode",
      description: "Would love to see dark mode in the dashboard",
      priority: "low",
      status: "resolved",
      assigned_to: "agent_002",
      created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
      resolved_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
      first_response_at: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: "ticket_004_other_def",
      customer_id: "customer_def",
      subject: "Account access issue",
      description: "Cannot login to my account",
      priority: "high",
      status: "open",
      assigned_to: null,
      created_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
      resolved_at: null,
      first_response_at: null,
    },
  ];

  // Filter by customer if role is customer (only see own tickets)
  let tickets = mockTicketData;
  if (role === "customer") {
    tickets = tickets.filter((t) => t.customer_id === userId);
  }

  // Apply filters
  if (statusFilter) {
    tickets = tickets.filter((t) => t.status === statusFilter);
  }
  if (priorityFilter) {
    tickets = tickets.filter((t) => t.priority === priorityFilter);
  }

  // Apply limit
  return tickets.slice(0, limit);
}
