# Founder Sheets sync and customer privacy boundary

## Architecture

Customer authentication remains Supabase-owned at `/login`. The founder dashboard at `/founder` is protected by `requireFounder()` and uses a server-only Google service account to update one private spreadsheet.

The service account can write only to the spreadsheet explicitly shared with its email. Its credential is never sent to the browser, never placed in `public/`, and never committed to Git.

The founder sync does **not** copy customer Google Sheets, customer memory, customer credentials, or customer-owned content into the founder ledger. It writes only server-derived business totals and safety/audit status.

## One-time setup

1. Create or select a Google Cloud project and enable Google Sheets API.
2. Create a service account and download its JSON key once.
3. Create a private Google Sheet with any title.
4. Share that Sheet with the service-account `client_email` as Editor.
5. Prefer a Render Secret File: upload the downloaded JSON as `google-service-account.json` and set these server-only variables in Render:

```text
GOOGLE_SHEETS_SPREADSHEET_ID=<the Sheet id>
GOOGLE_SERVICE_ACCOUNT_JSON_PATH=/etc/secrets/google-service-account.json
```

The base64url environment variable remains supported for hosts without Secret
Files, but the Secret File path is preferred because the key never needs to be
copied into an environment-variable textbox.

Do not add the key to GitHub, `.env` files committed to source, Cloudflare Worker code, browser storage, or customer-facing HTML.

## Runtime behavior

`POST /api/founder/sheets/sync`:

- requires a Supabase session;
- requires the user ID to be in `FOUNDER_USER_IDS`;
- rejects cross-origin requests;
- creates the six required tabs if missing;
- writes server-derived values with a bounded batch update;
- returns only sync status, tab count, and row count;
- logs a generic failure message without credential or sheet contents.

## Customer-owned Sheets and memory

Customer-owned Google Sheets should be an explicit, separate opt-in feature. The founder service account must never be granted access to customer sheets. A future customer connector should use a separate Google OAuth client, least-privilege scopes, explicit consent, revocation, and encrypted per-user token storage. Until that connector is configured and independently tested, customers can export or keep their data in their own Google account without any automatic founder-side copy.

## Verification checklist

- Founder dashboard opens only for an allowlisted Supabase user.
- Missing Google configuration returns a generic 503 and does not expose credentials.
- Non-founder callers receive 403.
- Cross-origin POSTs receive 403.
- A successful sync writes only the six documented tabs.
- Customer data is absent from the founder sheet payload.
- Rotate the service-account key immediately if it is ever exposed.
