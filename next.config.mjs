import { contentSecurityPolicy } from './config/content-security-policy.mjs';

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // Keep Render's Free-tier build from retaining prerender source maps and
  // preloading every route module while the page-data worker starts.
  productionBrowserSourceMaps: false,
  enablePrerenderSourceMaps: false,
  serverExternalPackages: ['googleapis'],
  // Render's Free instance cannot afford a second full TypeScript worker
  // after the production bundle. Run `npm run typecheck` locally/CI instead.
  typescript: {
    ignoreBuildErrors: true,
  },
  experimental: {
    // Keep the build bounded for Render's free-instance memory limit.
    // The CLI child process loses its captured JSON stream in this host.
    useTypeScriptCli: false,
    cpus: 1,
    webpackMemoryOptimizations: true,
    preloadEntriesOnStart: false,
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'Content-Security-Policy', value: contentSecurityPolicy() },
          { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains; preload' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        ],
      },
      {
        source: '/api/:path*',
        headers: [{ key: 'Cache-Control', value: 'no-store' }],
      },
      {
        source: '/.well-known/security.txt',
        headers: [
          { key: 'Content-Type', value: 'text/plain; charset=utf-8' },
          { key: 'Cache-Control', value: 'public, max-age=3600' },
        ],
      },
    ];
  },
};

export default nextConfig;
