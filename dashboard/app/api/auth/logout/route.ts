/**
 * POST /api/auth/logout
 * Clears session and CSRF cookies
 *
 * Called by: logout button in components
 */

import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    // Clear session cookies
    const response = NextResponse.json({ ok: true });

    response.cookies.delete("session_id");
    response.cookies.delete("csrf_token");
    response.cookies.delete("google_oauth_state");

    console.log("User logged out");

    return response;
  } catch (error) {
    console.error("Logout error:", error);
    return NextResponse.json(
      { error: "Failed to logout" },
      { status: 500 }
    );
  }
}
