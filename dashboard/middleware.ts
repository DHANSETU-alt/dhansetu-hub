/**
 * Next.js Middleware
 *
 * Protected Route Guard
 *
 * Routes:
 * - /dashboard/*   → requires authentication
 * - /smartbudget/* → requires authentication
 * - /auth/*        → public (login flow)
 * - /               → public (home page)
 *
 * Behavior:
 * - Valid session + non-expired cookie → allow access
 * - No session or expired cookie → redirect to /
 */

import { NextRequest, NextResponse } from "next/server";

// Routes that require authentication
const protectedRoutes = ["/dashboard", "/smartbudget"];

// Routes that are public
const publicRoutes = ["/", "/auth", "/api/auth"];

/**
 * Check if a session cookie is valid and not expired
 */
function isValidSession(request: NextRequest): boolean {
  const sessionId = request.cookies.get("session_id")?.value;

  if (!sessionId) {
    return false;
  }

  // Basic validation: session_id should be a non-empty hex string
  // In production: validate against database for actual expiry check
  return /^[a-f0-9]{64}$/.test(sessionId);
}

/**
 * Check if route is protected
 */
function isProtectedRoute(pathname: string): boolean {
  return protectedRoutes.some((route) => pathname.startsWith(route));
}

/**
 * Check if route is public
 */
function isPublicRoute(pathname: string): boolean {
  return publicRoutes.some((route) => pathname.startsWith(route));
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow all static assets and next internal routes
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/public") ||
    pathname.endsWith(".ico") ||
    pathname.endsWith(".png") ||
    pathname.endsWith(".jpg") ||
    pathname.endsWith(".svg") ||
    pathname.endsWith(".css") ||
    pathname.endsWith(".js")
  ) {
    return NextResponse.next();
  }

  // Allow public routes without authentication
  if (isPublicRoute(pathname)) {
    return NextResponse.next();
  }

  // Protect authenticated routes
  if (isProtectedRoute(pathname)) {
    const hasValidSession = isValidSession(request);

    if (!hasValidSession) {
      // Redirect to home page (with optional return URL for post-login redirect)
      const loginUrl = new URL("/", request.nextUrl.origin);
      loginUrl.searchParams.set("next", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

/**
 * Configure which routes the middleware applies to
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public (public files)
     */
    "/((?!_next/static|_next/image|favicon.ico|public).*)",
  ],
};
