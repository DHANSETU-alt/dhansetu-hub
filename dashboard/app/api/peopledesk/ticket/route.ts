/**
 * POST /api/peopledesk/ticket
 *
 * Create a new support ticket
 *
 * Request body:
 * {
 *   subject: string,
 *   description: string,
 *   priority?: "high" | "medium" | "low"
 * }
 *
 * Returns: Created ticket object with id, status, created_at, etc.
 */

import { NextRequest, NextResponse } from "next/server";
import { validateSession } from "@/lib/session-middleware";

export async function POST(req: NextRequest) {
  try {
    // Validate session
    const session = await validateSession(req);
    if (!session) {
      return NextResponse.json(
        { error: "Unauthorized: Invalid or expired session" },
        { status: 401 }
      );
    }

    const body = await req.json();
    const { subject, description, priority = "medium" } = body;

    // Validate required fields
    if (!subject || !description) {
      return NextResponse.json(
        { error: "Subject and description are required" },
        { status: 400 }
      );
    }

    if (!["high", "medium", "low"].includes(priority)) {
      return NextResponse.json(
        { error: "Priority must be high, medium, or low" },
        { status: 400 }
      );
    }

    // Generate ticket ID
    const ticketId = `ticket_${Date.now()}_${session.user_id.substring(0, 8)}`;
    const now = new Date().toISOString();

    const ticket = {
      id: ticketId,
      customer_id: session.user_id,
      subject,
      description,
      priority,
      status: "open",
      assigned_to: null,
      created_at: now,
      updated_at: now,
      resolved_at: null,
      first_response_at: null,
    };

    // TODO: Store in database
    // In production, call the Python orchestrator API to persist this

    return NextResponse.json(
      {
        success: true,
        data: ticket,
        meta: {
          userId: session.user_id,
          createdAt: now,
        },
      },
      { status: 201 }
    );
  } catch (error) {
    console.error("[peopledesk/ticket] Error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
