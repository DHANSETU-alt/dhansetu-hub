/**
 * GET /api/peopledesk/tickets/[id]
 * PATCH /api/peopledesk/tickets/[id]
 *
 * GET: Retrieve ticket details with comment thread
 * PATCH: Update ticket status/priority
 *
 * PATCH request body:
 * {
 *   status?: "open" | "in-progress" | "resolved",
 *   priority?: "high" | "medium" | "low",
 *   assigned_to?: string (support agent ID)
 * }
 */

import { NextRequest, NextResponse } from "next/server";
import { validateSession } from "@/lib/session-middleware";

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // Validate session
    const session = await validateSession(req);
    if (!session) {
      return NextResponse.json(
        { error: "Unauthorized: Invalid or expired session" },
        { status: 401 }
      );
    }

    const ticketId = params.id;

    // Retrieve ticket (in production, from database)
    const ticket = getMockTicket(ticketId);
    if (!ticket) {
      return NextResponse.json(
        { error: "Ticket not found" },
        { status: 404 }
      );
    }

    // Permission check: customer can only see their own tickets
    const userRole = session.user_id === "admin" ? "support" : "customer";
    if (userRole === "customer" && ticket.customer_id !== session.user_id) {
      return NextResponse.json(
        { error: "Forbidden: You can only view your own tickets" },
        { status: 403 }
      );
    }

    // Retrieve comments for this ticket
    const comments = getMockComments(ticketId);

    return NextResponse.json(
      {
        success: true,
        data: {
          ticket,
          comments,
          metrics: {
            response_time_minutes: calculateResponseTime(comments, ticket),
            resolution_time_hours: ticket.resolved_at
              ? Math.round(
                  (new Date(ticket.resolved_at).getTime() -
                    new Date(ticket.created_at).getTime()) /
                    (1000 * 60 * 60)
                )
              : null,
          },
        },
        meta: {
          userId: session.user_id,
          userRole,
          fetchedAt: new Date().toISOString(),
        },
      },
      { status: 200 }
    );
  } catch (error) {
    console.error("[peopledesk/tickets/[id]] Error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // Validate session
    const session = await validateSession(req);
    if (!session) {
      return NextResponse.json(
        { error: "Unauthorized: Invalid or expired session" },
        { status: 401 }
      );
    }

    // Check if user is support agent
    const userRole = session.user_id === "admin" ? "support" : "customer";
    if (userRole !== "support") {
      return NextResponse.json(
        { error: "Forbidden: Only support agents can update tickets" },
        { status: 403 }
      );
    }

    const ticketId = params.id;
    const body = await req.json();
    const { status, priority, assigned_to } = body;

    // Validate fields
    if (status && !["open", "in-progress", "resolved"].includes(status)) {
      return NextResponse.json(
        { error: "Invalid status" },
        { status: 400 }
      );
    }

    if (priority && !["high", "medium", "low"].includes(priority)) {
      return NextResponse.json(
        { error: "Invalid priority" },
        { status: 400 }
      );
    }

    // Get current ticket
    const ticket = getMockTicket(ticketId);
    if (!ticket) {
      return NextResponse.json(
        { error: "Ticket not found" },
        { status: 404 }
      );
    }

    // Update ticket (in production, update in database)
    const updatedTicket = {
      ...ticket,
      ...(status && { status }),
      ...(priority && { priority }),
      ...(assigned_to && { assigned_to }),
      updated_at: new Date().toISOString(),
    };

    return NextResponse.json(
      {
        success: true,
        data: updatedTicket,
        meta: {
          userId: session.user_id,
          updatedAt: new Date().toISOString(),
        },
      },
      { status: 200 }
    );
  } catch (error) {
    console.error("[peopledesk/tickets/[id] PATCH] Error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

// ============================================================================
// Mock Data Functions
// ============================================================================

function getMockTicket(ticketId: string): any | null {
  const mockTickets: Record<string, any> = {
    "ticket_001_cust_abc": {
      id: "ticket_001_cust_abc",
      customer_id: "customer_abc",
      subject: "Payment processing error on checkout",
      description: "Getting an error when trying to complete payment. Error code: 502",
      priority: "high",
      status: "open",
      assigned_to: null,
      created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      resolved_at: null,
      first_response_at: null,
    },
    "ticket_002_cust_abc": {
      id: "ticket_002_cust_abc",
      customer_id: "customer_abc",
      subject: "How to export data from dashboard",
      description: "Need help understanding how to export my data in CSV format",
      priority: "medium",
      status: "in-progress",
      assigned_to: "agent_001",
      created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
      resolved_at: null,
      first_response_at: new Date(Date.now() - 22 * 60 * 60 * 1000).toISOString(),
    },
  };

  return mockTickets[ticketId] || null;
}

function getMockComments(ticketId: string): any[] {
  const mockCommentData: Record<string, any[]> = {
    "ticket_001_cust_abc": [
      {
        id: "comment_001",
        ticket_id: "ticket_001_cust_abc",
        author_type: "customer",
        author_id: "customer_abc",
        author_name: "John Doe",
        message: "I've been trying to checkout all morning but keep getting a 502 error. Please help!",
        created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      },
    ],
    "ticket_002_cust_abc": [
      {
        id: "comment_002",
        ticket_id: "ticket_002_cust_abc",
        author_type: "customer",
        author_id: "customer_abc",
        author_name: "John Doe",
        message: "I need to export all my transaction history in CSV format",
        created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      },
      {
        id: "comment_003",
        ticket_id: "ticket_002_cust_abc",
        author_type: "support",
        author_id: "agent_001",
        author_name: "Sarah Support",
        message:
          "Thanks for reaching out! You can export your data from Settings > Export. Click the Export Data button and select CSV format.",
        created_at: new Date(Date.now() - 22 * 60 * 60 * 1000).toISOString(),
      },
      {
        id: "comment_004",
        ticket_id: "ticket_002_cust_abc",
        author_type: "customer",
        author_id: "customer_abc",
        author_name: "John Doe",
        message: "Perfect! Found it. Thanks for your help!",
        created_at: new Date(Date.now() - 20 * 60 * 60 * 1000).toISOString(),
      },
    ],
  };

  return mockCommentData[ticketId] || [];
}

function calculateResponseTime(comments: any[], ticket: any): number | null {
  if (!ticket.first_response_at) return null;
  const responseTime =
    new Date(ticket.first_response_at).getTime() -
    new Date(ticket.created_at).getTime();
  return Math.round(responseTime / (1000 * 60)); // Convert to minutes
}
