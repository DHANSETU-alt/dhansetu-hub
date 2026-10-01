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

// Real bug found live-testing the new Razorpay Checkout.js integration
// (blackboxops-os/pricing): the "Pay Now" button silently did nothing --
// no error, no network request to checkout.razorpay.com at all. Root
// cause confirmed via `curl -sI` on this page's own headers: this CSP's
// script-src/connect-src/frame-src had no Razorpay entries, so the
// browser blocked checkout.js from ever loading, before it could even
// report an error. Razorpay's own documented CSP requirements for
// Checkout.js: script-src for the loader, connect-src for its XHR calls,
// frame-src for the payment iframe it opens.
const RAZORPAY_SCRIPT = "https://checkout.razorpay.com";
const RAZORPAY_API = "https://api.razorpay.com";
const RAZORPAY_LUMBERJACK = "https://lumberjack.razorpay.com"; // Checkout.js's own client-side logging endpoint

const CSP = isProd
  ? [
      "default-src 'self'",
      `script-src 'self' ${RAZORPAY_SCRIPT}`,
      "style-src 'self' 'unsafe-inline'", // Tailwind/inline styles, no remote style host
      "img-src 'self' data: blob: https://*.razorpay.com",
      "font-src 'self'", // next/font/google self-hosts at build time -- no external font host needed
      `connect-src 'self' ${RAZORPAY_API} ${RAZORPAY_LUMBERJACK}`,
      `frame-src ${RAZORPAY_API}`,
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; ")
  : [
      "default-src 'self'",
      `script-src 'self' 'unsafe-eval' 'unsafe-inline' ${RAZORPAY_SCRIPT}`, // Fast Refresh requires eval in dev
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob: https://*.razorpay.com",
      "font-src 'self'",
      `connect-src 'self' ws: wss: ${RAZORPAY_API} ${RAZORPAY_LUMBERJACK}`, // ws:/wss: for HMR
      `frame-src ${RAZORPAY_API}`,
    ].join("; ");

// Real bug found + fixed 2026-09-13: Strict-Transport-Security was sent
// unconditionally, including in dev over plain HTTP -- unlike CSP just
// above, which already correctly branches on isProd. Chrome caches HSTS
// per-host (not per-origin/port) the moment it sees this header, then
// force-upgrades every later request to that host to HTTPS forever
// (up to max-age) -- this dev server has no TLS listener at all, so once
// cached, EVERY page on this host silently breaks with a real browser
// error page, confirmed live via a LAN-IP visit to /mission-control
// (curl saw a real 200; Chrome showed a hard error; get_page_text/
// screenshot both failed with "Frame with ID 0 is showing error page").
// HSTS only makes sense once this is actually served over real HTTPS.
const SECURITY_HEADERS = [
  ...(isProd ? [{ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" }] : []),
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
  // This Mac's own tailnet address is allowlisted too, for opening the
  // dashboard from another device on the tailnet. Shakthi_OS is Mac-only
  // as of 2026-09-08 -- the Linux tailnet address that used to be listed
  // here (for the now-retired Mac<->Linux bridge) is gone.
  allowedDevOrigins: ["127.0.0.1", "localhost", "100.117.111.80"],
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
};

export default nextConfig;
