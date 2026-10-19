import { createServerClient } from "@supabase/ssr";
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

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request });
  applySecurityHeaders(response);
  if (process.env.PAYMENT_FLOW_TEST_MODE === "1") {
    captureReferral(request, response);
    return response;
  }
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return response;

  const supabase = createServerClient(url, key, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll(values) {
        values.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        applySecurityHeaders(response);
        values.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, {
            ...options,
            ...(process.env.NEXT_PUBLIC_AUTH_COOKIE_DOMAIN
              ? { domain: process.env.NEXT_PUBLIC_AUTH_COOKIE_DOMAIN }
              : {}),
          }),
        );
      },
    },
  });
  await supabase.auth.getUser();
  // After the session refresh, because that block may replace `response`.
  captureReferral(request, response);
  return response;
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
