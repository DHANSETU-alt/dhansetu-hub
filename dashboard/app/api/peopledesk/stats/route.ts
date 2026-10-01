/**
 * GET /api/peopledesk/stats
 *
 * Retrieve support team dashboard statistics
 *
 * Returns:
 * {
 *   total_open: number,
 *   total_in_progress: number,
 *   total_resolved: number,
 *   avg_resolution_time_hours: number,
 *   avg_first_response_time_minutes: number,
 *   total_tickets: number,
 *   support_agents: Array<{id, name, email, availability_status, assigned_tickets_count}>,
 *   sla_breached: number,
 *   sla_at_risk: number
 * }
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

    // Check if user is support agent (admin in mock)
    const userRole = session.user_id === "admin" ? "support" : "customer";
    if (userRole !== "support") {
      return NextResponse.json(
        { error: "Forbidden: Only support agents can view stats" },
        { status: 403 }
      );
    }

    const stats = generateMockStats();

    return NextResponse.json(
      {
        success: true,
        data: stats,
        meta: {
          userId: session.user_id,
          userRole,
          fetchedAt: new Date().toISOString(),
          lastUpdated: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
        },
      },
      { status: 200 }
    );
  } catch (error) {
    console.error("[peopledesk/stats] Error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

function generateMockStats() {
  return {
    // Ticket Status Breakdown
    total_open: 12,
    total_in_progress: 8,
    total_resolved: 145,
    total_tickets: 165,

    // SLA Metrics
    avg_resolution_time_hours: 18.5,
    avg_first_response_time_minutes: 42,
    sla_breached: 2,
    sla_at_risk: 4,

    // Priority Distribution
    high_priority_open: 3,
    medium_priority_open: 7,
    low_priority_open: 2,

    // Support Agents
    support_agents: [
      {
        id: "agent_001",
        name: "Sarah Support",
        email: "sarah@support.com",
        availability_status: "available",
        assigned_tickets_count: 5,
      },
      {
        id: "agent_002",
        name: "Mike Help",
        email: "mike@support.com",
        availability_status: "busy",
        assigned_tickets_count: 8,
      },
      {
        id: "agent_003",
        name: "Lisa Care",
        email: "lisa@support.com",
        availability_status: "away",
        assigned_tickets_count: 3,
      },
    ],

    // Trend Data
    tickets_created_today: 5,
    tickets_resolved_today: 4,
    tickets_created_this_week: 28,
    tickets_resolved_this_week: 21,

    // Customer Satisfaction (mock data)
    avg_satisfaction_score: 4.2,
    satisfaction_responses: 24,

    // Peak Hours
    peak_hours: ["9:00-10:00", "14:00-15:00", "16:00-17:00"],
    busiest_day_of_week: "Tuesday",
  };
}
