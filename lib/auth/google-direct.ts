import { createPublicKey, verify as verifySignature } from "node:crypto";

export type GoogleIdentity = {
  sub: string;
  email: string;
  name?: string;
  picture?: string;
  email_verified: boolean;
  iss: string;
  aud: string | string[];
  exp: number;
};

type GoogleJwk = { kty: string; n: string; e: string; kid?: string; alg?: string; use?: string };
const GOOGLE_ISSUERS = new Set(["https://accounts.google.com", "accounts.google.com"]);

export function safeNextPath(value: string | null | undefined) {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/";
}

export function googleConfig() {
  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  const redirectUri = process.env.GOOGLE_REDIRECT_URI || `${process.env.NEXT_PUBLIC_APP_URL || "https://dhansetuhub.in"}/api/auth/google-direct/callback`;
  if (!clientId || !clientSecret) throw new Error("Direct Google OAuth is not configured");
  return { clientId, clientSecret, redirectUri };
}

function decodePart(value: string) {
  return Buffer.from(value, "base64url").toString("utf8");
}

export async function verifyGoogleIdToken(idToken: string, clientId: string): Promise<GoogleIdentity> {
  const parts = idToken.split(".");
  if (parts.length !== 3) throw new Error("Invalid Google ID token");
  const [encodedHeader, encodedPayload, encodedSignature] = parts;
  const header = JSON.parse(decodePart(encodedHeader)) as { alg?: string; kid?: string };
  const payload = JSON.parse(decodePart(encodedPayload)) as GoogleIdentity;
  if (header.alg !== "RS256" || !header.kid) throw new Error("Unsupported Google token signature");
  if (!GOOGLE_ISSUERS.has(payload.iss)) throw new Error("Invalid Google token issuer");
  if (!Array.isArray(payload.aud) ? payload.aud !== clientId : !payload.aud.includes(clientId)) throw new Error("Invalid Google token audience");
  if (!payload.email || !payload.email_verified || !payload.sub || payload.exp <= Math.floor(Date.now() / 1000)) throw new Error("Invalid or expired Google identity");
  const jwksResponse = await fetch("https://www.googleapis.com/oauth2/v3/certs", { cache: "no-store" });
  if (!jwksResponse.ok) throw new Error("Google signing keys unavailable");
  const jwks = (await jwksResponse.json()) as { keys?: GoogleJwk[] };
  const jwk = jwks.keys?.find((candidate) => candidate.kid === header.kid);
  if (!jwk) throw new Error("Google signing key not found");
  const publicKey = createPublicKey({ key: jwk as unknown as import("node:crypto").JsonWebKey, format: "jwk" });
  const valid = verifySignature("RSA-SHA256", Buffer.from(`${encodedHeader}.${encodedPayload}`), publicKey, Buffer.from(encodedSignature, "base64url"));
  if (!valid) throw new Error("Google token signature invalid");
  return payload;
}

export async function exchangeGoogleCode(code: string, config: ReturnType<typeof googleConfig>) {
  const response = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ code, client_id: config.clientId, client_secret: config.clientSecret, redirect_uri: config.redirectUri, grant_type: "authorization_code" }),
  });
  if (!response.ok) throw new Error("Google authorization code exchange failed");
  const tokens = (await response.json()) as { id_token?: string };
  if (!tokens.id_token) throw new Error("Google did not return an ID token");
  return tokens.id_token;
}
