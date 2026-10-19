/**
 * Client-Side Authentication Utilities
 *
 * Safe for use in client components ("use client")
 * Calls server-side endpoints for authentication checks
 */

export interface AuthContext {
  isAuthenticated: boolean;
  userEmail?: string;
  userId?: number;
  expiresAt?: string;
  error?: string;
}

/**
 * Check authentication status via API endpoint
 *
 * Called by: Client components
 */
export async function getAuthContext(): Promise<AuthContext> {
  try {
    const response = await fetch("/api/auth/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
      credentials: "include",
    });

    if (!response.ok) {
      return { isAuthenticated: false };
    }

    const session = await response.json();
    return {
      isAuthenticated: true,
      userEmail: session.user_email,
      userId: session.user_id,
      expiresAt: session.expires_at,
    };
  } catch (error) {
    console.error("[auth-client] Error getting auth context:", error);
    return {
      isAuthenticated: false,
      error: "Failed to retrieve auth context",
    };
  }
}

/**
 * Logout: Call server endpoint to clear session
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
    console.error("[auth-client] Logout error:", error);
  }
}
