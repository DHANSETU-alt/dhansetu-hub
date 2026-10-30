import { NextResponse, type NextRequest } from "next/server";
import { createServerSupabase, hasSupabasePublicConfig } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const url = request.nextUrl;
  const code = url.searchParams.get("code");
  const next = url.searchParams.get("next");
  const destination = next?.startsWith("/") && !next.startsWith("//") ? next : "/";
  // Render terminates TLS before the Next.js process, so request.url can expose the
  // internal 0.0.0.0:10000 origin. Always send users back to the canonical public host.
  const appOrigin = process.env.NEXT_PUBLIC_APP_URL?.replace(/\/$/, "") || url.origin;
  const redirectTo = (path: string) => NextResponse.redirect(new URL(path, appOrigin));
  if (!code) return redirectTo("/login?error=missing_auth_code");
  if (!hasSupabasePublicConfig()) return redirectTo("/login?error=auth_unavailable");
  const supabase = await createServerSupabase();
  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) return redirectTo("/login?error=oauth_callback_failed");
  return redirectTo(destination);
}
