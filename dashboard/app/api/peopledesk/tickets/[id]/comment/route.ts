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

    const commentId = `comment_${Date.now()}_${ticketId.substring(8, 16)}`;

    try {
      const orchestratorUrl = process.env.ORCHESTRATOR_URL || "http://localhost:8000";
      const addCommentResponse = await fetch(`${orchestratorUrl}/api/peopledesk/ticket-comment`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          comment_id: commentId,
          ticket_id: ticketId,
          author_type: authorType,
          author_id: session.user_id,
          message: message.trim(),
        }),
      });

      if (!addCommentResponse.ok) {
        return NextResponse.json(
          { error: "Failed to add comment" },
          { status: 500 }
        );
      }

      const comment = await addCommentResponse.json();

      return NextResponse.json(
        {
          success: true,
          data: comment,
          meta: {
            userId: session.user_id,
            authorType,
            createdAt: comment.created_at,
          },
        },
        { status: 201 }
      );
    } catch (orchestratorError) {
      console.error("[peopledesk/tickets/[id]/comment] Orchestrator error:", orchestratorError);
      return NextResponse.json(
        { error: "Failed to communicate with backend" },
        { status: 503 }
      );
    }
  } catch (error) {
    console.error("[peopledesk/tickets/[id]/comment] Error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
