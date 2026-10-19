/**
 * Authentication Utilities
 *
 * Handles:
 * - Session validation from cookies
 * - User context retrieval
 * - CSRF token validation
 * - Logout
 */

import { cookies } from "next/headers";

export interface SessionPayload {
  session_id: string;
  user_email: string;
  user_id: number;
  expires_at: string;
  csrf_token?: string;
}

export interface AuthContext {
  isAuthenticated: boolean;
  userEmail?: string;
  userId?: number;
  expiresAt?: string;
  error?: string;
}

/**
 * Get current session from httpOnly cookies
 *
 * Returns: SessionPayload | null
 *
 * Security:
 * - session_id: httpOnly, secure, sameSite=strict
 * - csrf_token: accessible to client for double-submit validation
 * - No tokens in URL or localStorage
 */
export async function getSession(): Promise<SessionPayload | null> {
  try {
    const cookieStore = await cookies();
    const sessionId = cookieStore.get("session_id")?.value;
    const csrfToken = cookieStore.get("csrf_token")?.value;

    if (!sessionId) {
      return null;
    }

    // Validate session against server (check expiry, etc)
    // In production: call /api/auth/validate to verify session is still valid
    const response = await fetch("/api/auth/validate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken || "",
      },
      body: JSON.stringify({ session_id: sessionId }),
    });

    if (!response.ok) {
      return null;
    }

    const session = await response.json();
    return {
      session_id: sessionId,
      csrf_token: csrfToken,
      ...session,
    };
  } catch (error) {
    console.error("Session retrieval error:", error);
    return null;
  }
}

/**
 * Check if user is authenticated
 *
 * Returns: boolean
 */
export async function isAuthenticated(): Promise<boolean> {
  const session = await getSession();
  return session !== null && !isSessionExpired(session);
}

/**
 * Check if session has expired
 */
function isSessionExpired(session: SessionPayload): boolean {
  if (!session.expires_at) return true;
  return new Date(session.expires_at) < new Date();
}

/**
 * Get auth context (authentication status + user info)
 *
 * Used by: protected pages, components that show user info
 */
export async function getAuthContext(): Promise<AuthContext> {
  try {
    const session = await getSession();

    if (!session || isSessionExpired(session)) {
      return { isAuthenticated: false };
    }

    return {
      isAuthenticated: true,
      userEmail: session.user_email,
      userId: session.user_id,
      expiresAt: session.expires_at,
    };
  } catch (error) {
    console.error("Auth context error:", error);
    return {
      isAuthenticated: false,
      error: "Failed to retrieve auth context",
    };
  }
}

/**
 * Validate CSRF token from form submission
 *
 * Called by: API routes that modify state
 *
 * Pattern: Double-submit cookie
 * - CSRF token in cookie (set by callback route)
 * - CSRF token in request header or form data
 * - Server validates both match
 */
export async function validateCsrfToken(
  requestToken: string
): Promise<boolean> {
  try {
    const cookieStore = await cookies();
    const cookieToken = cookieStore.get("csrf_token")?.value;

    if (!cookieToken || !requestToken) {
      return false;
    }

    // Constant-time comparison to prevent timing attacks
    return constantTimeEqual(requestToken, cookieToken);
  } catch (error) {
    console.error("CSRF validation error:", error);
    return false;
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
 * Logout: clear session cookies
 *
 * Called by: logout button, session expiry handler
 */
export async function logout(): Promise<void> {
  try {
    const response = await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "include",
    });

    if (response.ok) {
      // Redirect to home page
      if (typeof window !== "undefined") {
        window.location.href = "/";
      }
    }
  } catch (error) {
    console.error("Logout error:", error);
  }
}

/**
 * Start session expiry countdown
 *
 * Called by: layout.tsx or a provider component
 *
 * Shows a warning when session is about to expire (e.g., 5 minutes before)
 */
export async function setupSessionExpiryHandler(): Promise<void> {
  const session = await getSession();

  if (!session || !session.expires_at) {
    return;
  }

  const expiresAt = new Date(session.expires_at).getTime();
  const warningTime = 5 * 60 * 1000; // 5 minutes before expiry

  const checkExpiry = setInterval(async () => {
    const now = Date.now();
    const timeUntilExpiry = expiresAt - now;

    if (timeUntilExpiry <= 0) {
      clearInterval(checkExpiry);
      // Session expired, show message and redirect
      console.log("Session expired, logging out...");
      await logout();
    } else if (
      timeUntilExpiry <= warningTime &&
      timeUntilExpiry > warningTime - 1000
    ) {
      // Show warning (could be a toast notification)
      console.warn("Session expires in 5 minutes");
    }
  }, 60000); // Check every minute

  return;
}
