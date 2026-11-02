import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { googleConfig, safeNextPath } from "@/lib/auth/google-direct";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  try {
    const config = googleConfig();
    const state = randomUUID();
    const authUrl = new URL("https://accounts.google.com/o/oauth2/v2/auth");
    authUrl.search = new URLSearchParams({ client_id: config.clientId, redirect_uri: config.redirectUri, response_type: "code", scope: "openid email profile", state, prompt: "select_account" }).toString();
    const response = NextResponse.redirect(authUrl);
    const cookie = { httpOnly: true, sameSite: "lax" as const, secure: process.env.NODE_ENV === "production", maxAge: 600, path: "/" };
    response.cookies.set("google_direct_state", state, cookie);
    response.cookies.set("google_direct_next", safeNextPath(request.nextUrl.searchParams.get("next")), cookie);
    return response;
  } catch {
    return NextResponse.redirect(new URL("/login?error=google_direct_not_configured", request.url));
  }
}
