/**
 * Session Validation Middleware for Protected API Routes
 *
 * Usage:
 *   const session = await validateSession(req);
 *   if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
 *
 * Returns: SessionPayload | null
 */

import { NextRequest } from "next/server";
import { cookies } from "next/headers";

export interface SessionPayload {
  session_id: string;
  user_email: string;
  user_id: number;
  expires_at: string;
}

/**
 * Validate session from request cookies
 *
 * Checks:
 * - session_id cookie exists
 * - Session has not expired
 * - CSRF token matches (double-submit pattern)
 *
 * Returns: SessionPayload | null
 */
export async function validateSession(req: NextRequest): Promise<SessionPayload | null> {
  try {
    const cookieStore = await cookies();
    const sessionId = cookieStore.get("session_id")?.value;
    const csrfToken = cookieStore.get("csrf_token")?.value;

    if (!sessionId) {
      console.warn("[session-middleware] No session_id cookie found");
      return null;
    }

    // Validate CSRF token from request header
    const requestCsrfToken = req.headers.get("X-CSRF-Token");
    if (requestCsrfToken && csrfToken && !constantTimeEqual(requestCsrfToken, csrfToken)) {
      console.warn("[session-middleware] CSRF token mismatch");
      return null;
    }

    // Call /api/auth/validate to verify session is still valid
    // This ensures session hasn't expired and user is still active
    const response = await fetch(`${process.env.NEXTAUTH_URL || "http://localhost:3000"}/api/auth/validate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken || "",
      },
      body: JSON.stringify({ session_id: sessionId }),
    });

    if (!response.ok) {
      console.warn(`[session-middleware] Session validation failed: ${response.status}`);
      return null;
    }

    const sessionData = await response.json();
    return {
      session_id: sessionId,
      ...sessionData,
    };
  } catch (error) {
    console.error("[session-middleware] Error validating session:", error);
    return null;
  }
}

/**
 * Constant-time string comparison
 * Prevents timing-based attacks on CSRF token validation
 */
function constantTimeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;

  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}

/**
 * Validate CSRF token from form submission
 *
 * Called by: API routes that modify state (POST/PUT/DELETE)
 *
 * Pattern: Double-submit cookie
 * - CSRF token in cookie (set by callback route)
 * - CSRF token in request header or form data
 * - Server validates both match
 */
export async function validateCsrfToken(requestToken: string): Promise<boolean> {
  try {
    const cookieStore = await cookies();
    const cookieToken = cookieStore.get("csrf_token")?.value;

    if (!cookieToken || !requestToken) {
      return false;
    }

    return constantTimeEqual(requestToken, cookieToken);
  } catch (error) {
    console.error("[session-middleware] CSRF validation error:", error);
    return false;
  }
}
