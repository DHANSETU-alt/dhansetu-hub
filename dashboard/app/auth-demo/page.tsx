/**
 * /auth-demo
 *
 * Test page for Google Sign-In implementation
 *
 * Shows:
 * 1. Login button (if not authenticated)
 * 2. User info + logout button (if authenticated)
 * 3. Session cookie details (dev only)
 */

"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getAuthContext, logout } from "@/lib/auth";
import type { AuthContext } from "@/lib/auth";

export default function AuthDemoPage() {
  const router = useRouter();
  const [authContext, setAuthContext] = useState<AuthContext | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function checkAuth() {
      const context = await getAuthContext();
      setAuthContext(context);
      setIsLoading(false);
    }
    checkAuth();
  }, []);

  async function handleLogout() {
    await logout();
    router.push("/");
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block">
            <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          </div>
          <p className="mt-4 text-slate-600">Loading authentication status...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">
            Authentication Demo
          </h1>
          <p className="text-slate-600">
            Phase 2 Task #4: Google Sign-In End-to-End Implementation
          </p>
        </div>

        {/* Status Card */}
        <div className="bg-white rounded-lg shadow-lg border border-slate-200 p-8 mb-8">
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-4">
              <div
                className={`w-3 h-3 rounded-full ${
                  authContext?.isAuthenticated
                    ? "bg-green-500"
                    : "bg-red-500"
                }`}
              />
              <h2 className="text-2xl font-semibold text-slate-900">
                {authContext?.isAuthenticated
                  ? "Authenticated"
                  : "Not Authenticated"}
              </h2>
            </div>
            <p className="text-slate-600">
              {authContext?.isAuthenticated
                ? "You are logged in with a valid session."
                : "No valid session found. Please log in."}
            </p>
          </div>

          {/* User Info */}
          {authContext?.isAuthenticated && (
            <div className="bg-slate-50 rounded-lg p-4 mb-6 space-y-3">
              <div>
                <label className="text-sm font-semibold text-slate-600">
                  Email
                </label>
                <p className="text-slate-900 font-mono">
                  {authContext.userEmail}
                </p>
              </div>
              <div>
                <label className="text-sm font-semibold text-slate-600">
                  User ID
                </label>
                <p className="text-slate-900 font-mono">{authContext.userId}</p>
              </div>
              <div>
                <label className="text-sm font-semibold text-slate-600">
                  Session Expires
                </label>
                <p className="text-slate-900 font-mono">
                  {authContext.expiresAt
                    ? new Date(authContext.expiresAt).toLocaleString()
                    : "Unknown"}
                </p>
              </div>
            </div>
          )}

          {/* Error */}
          {authContext?.error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <p className="text-red-800 font-semibold">Error</p>
              <p className="text-red-700 text-sm">{authContext.error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            {!authContext?.isAuthenticated ? (
              <>
                <a
                  href="/login"
                  className="flex-1 bg-blue-600 text-white font-semibold py-3 px-4 rounded-lg hover:bg-blue-700 transition-colors text-center"
                >
                  Go to Login
                </a>
              </>
            ) : (
              <>
                <button
                  onClick={handleLogout}
                  className="flex-1 bg-red-600 text-white font-semibold py-3 px-4 rounded-lg hover:bg-red-700 transition-colors"
                >
                  Logout
                </button>
                <a
                  href="/dashboard"
                  className="flex-1 bg-green-600 text-white font-semibold py-3 px-4 rounded-lg hover:bg-green-700 transition-colors text-center"
                >
                  Go to Dashboard
                </a>
              </>
            )}
          </div>
        </div>

        {/* Implementation Details */}
        <div className="bg-white rounded-lg shadow-lg border border-slate-200 p-8 space-y-6">
          <div>
            <h3 className="text-xl font-semibold text-slate-900 mb-3">
              ✓ Completed Components
            </h3>
            <ul className="space-y-2 text-slate-700">
              <li className="flex items-start gap-2">
                <span className="text-green-600 font-bold mt-0.5">✓</span>
                <span>Database schema: users and sessions tables</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-600 font-bold mt-0.5">✓</span>
                <span>
                  API routes: /api/auth/google (initiate) and /api/auth/google/callback
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-600 font-bold mt-0.5">✓</span>
                <span>
                  Session management: httpOnly cookies + HMAC-SHA256 signing
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-600 font-bold mt-0.5">✓</span>
                <span>CSRF protection: Double-submit cookie pattern</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-600 font-bold mt-0.5">✓</span>
                <span>
                  Middleware: Protected routes redirect unauthenticated users
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-600 font-bold mt-0.5">✓</span>
                <span>Auth utilities: session validation, logout, CSRF checks</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-600 font-bold mt-0.5">✓</span>
                <span>Login page with Google Sign-In button</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-600 font-bold mt-0.5">✓</span>
                <span>Environment configuration: .env.local.example updated</span>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-xl font-semibold text-slate-900 mb-3">
              🔧 Configuration Required
            </h3>
            <div className="bg-slate-50 rounded-lg p-4 text-sm text-slate-700 space-y-2">
              <p>
                <strong>1. Create Google OAuth credentials:</strong>
              </p>
              <ol className="list-decimal list-inside space-y-1 ml-2">
                <li>
                  Go to{" "}
                  <a
                    href="https://console.cloud.google.com"
                    target="_blank"
                    rel="noopener"
                    className="text-blue-600 hover:underline"
                  >
                    Google Cloud Console
                  </a>
                </li>
                <li>Create a new OAuth 2.0 application</li>
                <li>
                  Add authorized redirect URI:
                  <code className="block mt-1 bg-white p-2 rounded border border-slate-200">
                    http://localhost:3000/api/auth/google/callback
                  </code>
                </li>
                <li>Copy Client ID and Secret</li>
              </ol>

              <p className="mt-4">
                <strong>2. Create .env.local:</strong>
              </p>
              <code className="block bg-white p-2 rounded border border-slate-200 text-xs">
                {`cp .env.local.example .env.local
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
SESSION_SECRET=$(openssl rand -hex 32)`}
              </code>

              <p className="mt-4">
                <strong>3. Restart Next.js dev server</strong>
              </p>
              <code className="block bg-white p-2 rounded border border-slate-200 text-xs">
                npm run dev
              </code>
            </div>
          </div>

          <div>
            <h3 className="text-xl font-semibold text-slate-900 mb-3">
              📋 Testing Checklist
            </h3>
            <ul className="space-y-2 text-slate-700">
              <li className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  disabled
                  defaultChecked={false}
                />
                <span>Render "Login with Google" button on /login</span>
              </li>
              <li className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  disabled
                  defaultChecked={false}
                />
                <span>
                  Click button → redirected to Google Consent Screen
                </span>
              </li>
              <li className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  disabled
                  defaultChecked={false}
                />
                <span>
                  After consent → redirected to /dashboard with session cookie
                </span>
              </li>
              <li className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  disabled
                  defaultChecked={false}
                />
                <span>Session cookie visible in DevTools (httpOnly flag)</span>
              </li>
              <li className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  disabled
                  defaultChecked={false}
                />
                <span>Log: "User authenticated: email@domain.com" in console</span>
              </li>
              <li className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  disabled
                  defaultChecked={false}
                />
                <span>Session expiry → automatic redirect to /login</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
