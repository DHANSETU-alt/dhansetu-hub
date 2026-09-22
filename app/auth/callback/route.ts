import { NextResponse, type NextRequest } from "next/server";
import { createServerSupabase, hasSupabasePublicConfig } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const url = request.nextUrl;
  const code = url.searchParams.get("code");
  const next = url.searchParams.get("next");
  const destination = next?.startsWith("/") && !next.startsWith("//") ? next : "/";
  if (!code) return NextResponse.redirect(new URL("/login?error=missing_auth_code", request.url));
  if (!hasSupabasePublicConfig()) return NextResponse.redirect(new URL("/login?error=auth_unavailable", request.url));
  const supabase = await createServerSupabase();
  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) return NextResponse.redirect(new URL("/login?error=oauth_callback_failed", request.url));
  return NextResponse.redirect(new URL(destination, request.url));
}
