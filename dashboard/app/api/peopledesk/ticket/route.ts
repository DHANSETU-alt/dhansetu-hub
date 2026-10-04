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

    try {
      const orchestratorUrl = process.env.ORCHESTRATOR_URL || "http://localhost:8000";
      const createResponse = await fetch(`${orchestratorUrl}/api/peopledesk/support-ticket`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ticket_id: ticketId,
          customer_id: session.user_id,
          subject,
          description,
          priority,
        }),
      });

      if (!createResponse.ok) {
        return NextResponse.json(
          { error: "Failed to create ticket in database" },
          { status: 500 }
        );
      }

      const ticket = await createResponse.json();

      return NextResponse.json(
        {
          success: true,
          data: ticket,
          meta: {
            userId: session.user_id,
            createdAt: ticket.created_at,
          },
        },
        { status: 201 }
      );
    } catch (orchestratorError) {
      console.error("[peopledesk/ticket] Orchestrator error:", orchestratorError);
      return NextResponse.json(
        { error: "Failed to communicate with backend" },
        { status: 503 }
      );
    }
  } catch (error) {
    console.error("[peopledesk/ticket] Error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
