/**
 * POST /api/peopledesk/tickets/[id]/comment
 *
 * Add a comment to a support ticket
 *
 * Request body:
 * {
 *   message: string
 * }
 *
 * Returns: Created comment object
 */

import { NextRequest, NextResponse } from "next/server";
import { validateSession } from "@/lib/session-middleware";

export async function POST(
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
    const body = await req.json();
    const { message } = body;

    // Validate message
    if (!message || typeof message !== "string" || message.trim().length === 0) {
      return NextResponse.json(
        { error: "Message is required and must be non-empty" },
        { status: 400 }
      );
    }

    if (message.length > 5000) {
      return NextResponse.json(
        { error: "Message cannot exceed 5000 characters" },
        { status: 400 }
      );
    }

    // Verify ticket exists (in production, query database)
    const ticketExists = ticketId.startsWith("ticket_");
    if (!ticketExists) {
      return NextResponse.json(
        { error: "Ticket not found" },
        { status: 404 }
      );
    }

    // Determine author type based on session
    const authorType = session.user_id === "admin" ? "support" : "customer";

    // Create comment
    const commentId = `comment_${Date.now()}_${ticketId.substring(8, 16)}`;
    const now = new Date().toISOString();

    const comment = {
      id: commentId,
      ticket_id: ticketId,
      author_type: authorType,
      author_id: session.user_id,
      message: message.trim(),
      created_at: now,
    };

    // TODO: Store in database
    // In production, call the Python orchestrator API to persist this
    // This should also update the ticket's updated_at timestamp
    // If support agent responds, also set first_response_at if not already set

    return NextResponse.json(
      {
        success: true,
        data: comment,
        meta: {
          userId: session.user_id,
          authorType,
          createdAt: now,
        },
      },
      { status: 201 }
    );
  } catch (error) {
    console.error("[peopledesk/tickets/[id]/comment] Error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
