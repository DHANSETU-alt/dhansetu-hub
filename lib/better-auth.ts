import { mkdirSync } from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";
import { betterAuth } from "better-auth";

const memoryDirectory = path.join(process.cwd(), ".gvc", "memory");
mkdirSync(memoryDirectory, { recursive: true });

const googleClientId = process.env.GOOGLE_CLIENT_ID;
const googleClientSecret = process.env.GOOGLE_CLIENT_SECRET;
const githubClientId = process.env.GITHUB_CLIENT_ID;
const githubClientSecret = process.env.GITHUB_CLIENT_SECRET;
const socialProviders = {
  ...(googleClientId && googleClientSecret ? { google: { clientId: googleClientId, clientSecret: googleClientSecret } } : {}),
  ...(githubClientId && githubClientSecret ? { github: { clientId: githubClientId, clientSecret: githubClientSecret } } : {}),
};

/**
 * DhanSetu's application auth plane is self-hosted and independent of
 * Supabase Auth. The SQLite file is local evidence/runtime state until the
 * approved production database migration is completed.
 */
export const auth = betterAuth({
  database: new Database(path.join(memoryDirectory, "auth.db")),
  baseURL: process.env.BETTER_AUTH_URL || process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
  basePath: "/api/auth",
  secret: process.env.BETTER_AUTH_SECRET || "local-only-change-BETTER_AUTH_SECRET-before-release",
  trustedOrigins: [process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000"],
  emailAndPassword: {
    enabled: true,
    autoSignIn: true,
  },
  socialProviders,
  session: {
    expiresIn: 60 * 60 * 24 * 7,
  },
});
