import { NextResponse, type NextRequest } from "next/server";
import {
  REFERRAL_COOKIE,
  REFERRAL_MAX_AGE_SECONDS,
  normaliseReferralCode,
} from "@/lib/partners/referral";

/**
 * Remembers which partner introduced this visitor. First touch wins, so a later link cannot
 * take credit from the partner who actually brought them.
 */
function captureReferral(request: NextRequest, response: NextResponse) {
  if (request.cookies.get(REFERRAL_COOKIE)) return;
  const code = normaliseReferralCode(request.nextUrl.searchParams.get("ref"));
  if (!code) return;
  response.cookies.set(REFERRAL_COOKIE, code, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: REFERRAL_MAX_AGE_SECONDS,
    path: "/",
  });
}

function applySecurityHeaders(response: NextResponse) {
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  if (process.env.NODE_ENV === "production") {
    response.headers.set("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
  }
}

function hasBetterAuthSessionCookie(request: NextRequest) {
  return request.cookies.has("better-auth.session_token") || request.cookies.has("__Secure-better-auth.session_token");
}

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request });
  applySecurityHeaders(response);
  if (process.env.PAYMENT_FLOW_TEST_MODE === "1") {
    captureReferral(request, response);
    return response;
  }
  captureReferral(request, response);
  const protectedPath = request.nextUrl.pathname.startsWith("/client/") || request.nextUrl.pathname.startsWith("/dashboard/1cr");
  if (protectedPath && !hasBetterAuthSessionCookie(request)) {
    return NextResponse.redirect(new URL(`/login?next=${encodeURIComponent(request.nextUrl.pathname)}`, request.url));
  }
  return response;
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
