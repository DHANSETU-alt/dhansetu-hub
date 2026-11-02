import { NextRequest, NextResponse } from "next/server";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { createServerSupabase } from "@/lib/supabase/server";
import { exchangeGoogleCode, googleConfig, safeNextPath, verifyGoogleIdToken } from "@/lib/auth/google-direct";

export const runtime = "nodejs";

async function ensureUser(email: string, identity: { sub: string; name?: string; picture?: string }) {
  const admin = createAdminSupabase();
  const created = await admin.auth.admin.createUser({ email, email_confirm: true, user_metadata: { google_sub: identity.sub, full_name: identity.name, avatar_url: identity.picture } });
  if (!created.error && created.data.user) return created.data.user;
  const listed = await admin.auth.admin.listUsers({ page: 1, perPage: 1000 });
  const existing = listed.data.users.find((user) => user.email?.toLowerCase() === email.toLowerCase());
  if (!existing) throw new Error("Could not provision the Google account");
  return existing;
}

export async function GET(request: NextRequest) {
  const fallback = new URL("/login?error=google_direct_failed", request.url);
  try {
    const code = request.nextUrl.searchParams.get("code");
    const state = request.nextUrl.searchParams.get("state");
    const storedState = request.cookies.get("google_direct_state")?.value;
    if (!code || !state || !storedState || state !== storedState) return NextResponse.redirect(fallback);
    const config = googleConfig();
    const identity = await verifyGoogleIdToken(await exchangeGoogleCode(code, config), config.clientId);
    const user = await ensureUser(identity.email, identity);
    const admin = createAdminSupabase();
    const link = await admin.auth.admin.generateLink({ type: "magiclink", email: user.email! });
    const tokenHash = link.data.properties?.hashed_token;
    if (link.error || !tokenHash) throw new Error("Could not create a session handoff");
    const supabase = await createServerSupabase();
    const verified = await supabase.auth.verifyOtp({ token_hash: tokenHash, type: "magiclink" });
    if (verified.error) throw verified.error;
    const destination = safeNextPath(request.cookies.get("google_direct_next")?.value);
    const response = NextResponse.redirect(new URL(destination, request.url));
    response.cookies.delete("google_direct_state");
    response.cookies.delete("google_direct_next");
    return response;
  } catch (error) {
    console.error("Direct Google OAuth failed", error instanceof Error ? error.message : "unknown error");
    return NextResponse.redirect(fallback);
  }
}
