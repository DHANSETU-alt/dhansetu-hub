/**
 * POST /api/auth/google
 * Initiates Google OAuth 2.0 flow
 *
 * Redirects to Google Consent Screen with:
 * - CLIENT_ID, redirect_uri, scopes
 * - State parameter (CSRF protection)
 */

import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";

export async function POST(req: NextRequest) {
  try {
    // Validate environment variables
    const clientId = process.env.GOOGLE_CLIENT_ID;
    const redirectUri = process.env.GOOGLE_REDIRECT_URI;

    if (!clientId || !redirectUri) {
      console.error("Missing Google OAuth environment variables");
      return NextResponse.json(
        { error: "OAuth credentials not configured" },
        { status: 500 }
      );
    }

    // Generate CSRF state parameter (random 32-byte hex)
    const state = crypto.randomBytes(32).toString("hex");

    // Store state in session/cookie for validation in callback
    // Using a secure, httpOnly cookie
    const response = NextResponse.json({ ok: true });
    response.cookies.set("google_oauth_state", state, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "strict",
      maxAge: 600, // 10 minutes
    });

    // Build Google Consent Screen URL
    const params = new URLSearchParams({
      client_id: clientId,
      redirect_uri: redirectUri,
      response_type: "code",
      scope: "openid email profile",
      state: state,
      access_type: "offline", // Request refresh token
      prompt: "select_account", // Allow user to choose account
    });

    const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;

    return NextResponse.json(
      {
        ok: true,
        redirect_url: googleAuthUrl,
      },
      { headers: response.headers }
    );
  } catch (error) {
    console.error("Google OAuth initiation error:", error);
    return NextResponse.json(
      { error: "Failed to initiate Google login" },
      { status: 500 }
    );
  }
}
