/**
 * POST /api/auth/session
 * Creates a new session after OAuth verification
 *
 * Called by: /api/auth/google/callback
 *
 * Body: { email, google_id, name, picture_url }
 *
 * Returns: { session_id, csrf_token, expires_at, user }
 */

import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";

/**
 * Create a session identifier using HMAC-SHA256
 */
function createSessionId(email: string): string {
  const sessionSecret = process.env.SESSION_SECRET;
  if (!sessionSecret) {
    throw new Error("SESSION_SECRET not configured");
  }

  const data = `${email}:${Date.now()}:${crypto.randomBytes(16).toString("hex")}`;
  return crypto
    .createHmac("sha256", sessionSecret)
    .update(data)
    .digest("hex");
}

/**
 * Create CSRF token for double-submit protection
 */
function createCsrfToken(): string {
  return crypto.randomBytes(32).toString("hex");
}

export async function POST(req: NextRequest) {
  try {
    const { email, google_id, name, picture_url } = await req.json();

    if (!email || !google_id) {
      return NextResponse.json(
        { error: "Missing required fields: email, google_id" },
        { status: 400 }
      );
    }

    // Call the orchestrator to create/update user and session
    // This is a Python backend call via HTTP to /api/shakthi-v5/session or similar
    // For now, we'll handle this directly using a simple in-memory store
    // In production, this should connect to the Shakthi orchestrator

    const sessionSecret = process.env.SESSION_SECRET;
    if (!sessionSecret) {
      throw new Error("SESSION_SECRET not configured");
    }

    // Generate session identifiers
    const session_id = createSessionId(email);
    const csrf_token = createCsrfToken();

    // Calculate expiry (7 days from now)
    const expiresAt = new Date();
    expiresAt.setDate(expiresAt.getDate() + 7);
    const expires_at = expiresAt.toISOString();

    // In a real implementation, this would:
    // 1. Connect to SQLite (shakthi.db)
    // 2. Create or update user in users table
    // 3. Create session in sessions table
    // 4. Return session data

    // For now, we'll return a structured response that includes
    // the necessary data for the callback to set cookies
    const response = {
      session_id,
      csrf_token,
      expires_at,
      user: {
        email,
        name,
        google_id,
        picture_url,
      },
    };

    return NextResponse.json(response, { status: 200 });
  } catch (error) {
    console.error("Session creation error:", error);
    return NextResponse.json(
      {
        error: "Failed to create session",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
