# DhanSetu direct Google sign-in bridge

## Why this exists

The Supabase Google OAuth provider is currently disabled for the project. The
old client call to `signInWithOAuth({ provider: "google" })` therefore fails
before Google sign-in starts with `Unsupported provider: provider is not
enabled`.

This bridge keeps DhanSetu's existing Supabase `auth.users` UUIDs, billing
ownership, GST data, and server-side session cookies. It does not use Firebase
or replace the database. The flow is:

1. The browser starts `/api/auth/google-direct/start`.
2. Google returns an authorization code to
   `/api/auth/google-direct/callback`.
3. The server exchanges the code and verifies the Google ID-token signature,
   issuer, audience, expiry, subject, and verified email against Google's
   published JWKS.
4. The server creates or finds the matching Supabase user with the service
   role, generates a one-time Supabase magic-link token, and consumes that
   token server-side with `verifyOtp`.
5. The normal Supabase SSR cookies are set and the user is redirected to the
   requested internal path.

No Google client secret or Supabase service-role key is sent to the browser.
The `next` path is restricted to an internal single-slash path to prevent an
open redirect.

## Required server configuration

Set these in the DhanSetu server environment, not in client JavaScript:

```env
GOOGLE_CLIENT_ID=your-web-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-web-client-secret
GOOGLE_REDIRECT_URI=https://dhansetuhub.in/api/auth/google-direct/callback
```

The Google Cloud OAuth web-client must contain this exact authorized redirect
URI. The existing Supabase URL, anon key, and service-role key must also be
present. The service-role key must remain server-only.

## Safe rollout checklist

- Add the redirect URI in Google Cloud Console.
- Add the three environment variables to the actual DhanSetu runtime.
- Restart/redeploy the DhanSetu server through the approved deployment path.
- Open `/login`, select **Continue with Google**, and confirm the browser
  returns to the checkout/dashboard without an `Unsupported provider` error.
- Confirm the session cookies are `HttpOnly`/secure in production and that no
  secret appears in browser source or network query parameters.
- Keep email/password available as the fallback while the direct bridge is
  being verified.

This code is locally typechecked and covered by the existing DhanSetu test
suite, but the live Google flow cannot be claimed complete until the Google
Cloud credentials and redirect URI are configured and a real browser callback
has succeeded.

## Alternative considered

Firebase Authentication can be connected to Supabase as a third-party identity
provider, but that is a broader migration for the current app: existing tables
reference Supabase `auth.users(id)` UUIDs and their RLS policies. It is not the
fastest safe fix for this production login failure. The direct Google bridge
avoids changing those ownership relationships.
