/**
 * POST /api/auth/validate
 * Validates session and returns user information
 *
 * Called by: lib/auth.ts getSession()
 *
 * Body: { session_id }
 * Headers: X-CSRF-Token (for double-submit CSRF protection)
 *
 * Returns: { user_email, user_id, expires_at } or 401
 */

import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const { session_id } = await req.json();
    const csrfToken = req.headers.get("X-CSRF-Token");

    if (!session_id) {
      return NextResponse.json(
        { error: "Missing session_id" },
        { status: 400 }
      );
    }

    // In production: validate session against database
    // Check:
    // 1. Session exists in sessions table
    // 2. Session has not expired (expires_at > now)
    // 3. CSRF token matches (double-submit pattern)
    // 4. User is still active

    // For now, basic validation:
    if (!/^[a-f0-9]{64}$/.test(session_id)) {
      return NextResponse.json(
        { error: "Invalid session format" },
        { status: 401 }
      );
    }

    // Retrieve session from store or mock it
    // In production: query sessions table from database
    // For now, return mock session with realistic expiry

    // Check if session has a stored expiry time
    // For development, extend session by 7 days
    const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();

    // Extract user info from session_id pattern
    // In production: look up user from database session table
    const mockSession = {
      user_email: "user@example.com",
      user_id: Math.floor(Math.random() * 10000) + 1,
      expires_at: expiresAt,
    };

    return NextResponse.json(mockSession, { status: 200 });
  } catch (error) {
    console.error("Session validation error:", error);
    return NextResponse.json(
      { error: "Failed to validate session" },
      { status: 401 }
    );
  }
}
