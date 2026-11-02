# Supabase Auth replacement: Better Auth

## Local migration status

DhanSetu authentication has been moved from Supabase Auth to Better Auth for
local development and verification. Supabase remains only as the existing GST,
billing, and workspace data boundary until a separately approved database
migration is completed.

Better Auth stores its local identity/session tables in:

```text
.gvc/memory/auth.db
```

The schema is generated and migrated from the current Better Auth configuration
and contains `user`, `session`, `account`, and `verification` tables.

## What changed

- Login uses Better Auth email/password and code-configured Google/GitHub
  social providers.
- `/api/auth/[...all]` is the Better Auth handler.
- Server pages and payment request authentication validate Better Auth sessions.
- Middleware performs an optimistic protected-route redirect; protected server
  pages and API routes perform the authoritative session check.
- The old Supabase OAuth callback and direct Google bridge are no longer used.
- No Supabase provider dashboard setting is needed for the Better Auth Google
  provider.

## Required before release

Set a long random `BETTER_AUTH_SECRET`, `BETTER_AUTH_URL`, and the Google
OAuth client credentials in the approved runtime environment. Configure the
Google provider callback as:

```text
https://dhansetuhub.in/api/auth/callback/google
```

Better Auth owns this callback under its `/api/auth` route; verify the final
origin before any public deployment.

The local SQLite identity IDs are not automatically the same as legacy
Supabase `auth.users` IDs. Existing billing/GST data must therefore be mapped
through an approved migration before a production cutover. This is why the
public deployment remains blocked and no existing Supabase data was deleted.

## Evidence boundary

Local email signup and session creation were verified on an isolated DhanSetu
server. Google social login is code-configured but cannot complete until
`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are supplied. No payment,
deployment, or public release was performed.
