import type { NextConfig } from "next";

// Real gap found auditing the live blackboxops.co.in site (WEB-001 audit,
// this session): 0/5 of these headers present. Can't land this fix on the
// actual live site until we know which of the 5 candidate repos is real
// (see LAUNCH_CHECKLIST.md) -- but this internal dashboard serves the
// blackboxOps_OS staging pages today, so it gets the fix now rather than
// waiting on that answer. CSP is looser in dev on purpose: Next.js's own
// Fast Refresh needs 'unsafe-eval'/'unsafe-inline' to work at all, and a
// dev server that can't hot-reload isn't a security win, it's just broken.
const isProd = process.env.NODE_ENV === "production";

const CSP = isProd
  ? [
      "default-src 'self'",
      "script-src 'self'",
      "style-src 'self' 'unsafe-inline'", // Tailwind/inline styles, no remote style host
      "img-src 'self' data: blob:",
      "font-src 'self'", // next/font/google self-hosts at build time -- no external font host needed
      "connect-src 'self'",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; ")
  : [
      "default-src 'self'",
      "script-src 'self' 'unsafe-eval' 'unsafe-inline'", // Fast Refresh requires eval in dev
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob:",
      "font-src 'self'",
      "connect-src 'self' ws: wss:", // HMR websocket
    ].join("; ");

const SECURITY_HEADERS = [
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Content-Security-Policy", value: CSP },
];

const nextConfig: NextConfig = {
  // Desktop launchers open the local dashboard through 127.0.0.1 while
  // `next dev` binds as localhost. Without this explicit local-only allow
  // entry, Next blocks the client chunks and Mission Control never hydrates,
  // leaving its React Flow canvas blank.
  //
  // The Mac<->Linux Tailscale bridge (2026-09-06) hits the same wall from
  // the other direction: opening either machine's dashboard via its
  // tailnet IP (not 127.0.0.1/localhost) gets its dev-resource chunks
  // blocked the same way, confirmed via a real "Blocked cross-origin
  // request" warning in Linux's dashboard.log. Both machines' known
  // tailnet addresses are allowlisted here so the same next.config.ts,
  // synced to both, works from either side.
  allowedDevOrigins: ["127.0.0.1", "localhost", "100.86.74.97", "100.117.111.80"],
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
};

export default nextConfig;
