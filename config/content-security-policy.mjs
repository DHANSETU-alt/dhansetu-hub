// Compatibility policy for the existing statically rendered Next.js application.
// Inline Next.js hydration scripts are retained; this is not a nonce-based strict CSP.
function httpsOrigin(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password ? url.origin : null;
  } catch { return null; }
}

export function contentSecurityPolicy(env = process.env) {
  const isDev = env.NODE_ENV !== 'production';
  const posthog = httpsOrigin(env.NEXT_PUBLIC_POSTHOG_HOST ?? 'https://app.posthog.com');
  const supabase = httpsOrigin(env.NEXT_PUBLIC_SUPABASE_URL ?? '');
  const unique = (values) => Array.from(new Set(values.filter(Boolean))).join(' ');
  const directives = {
    'default-src': ["'self'"],
    'script-src': ["'self'", "'unsafe-inline'", isDev && "'unsafe-eval'", 'https://checkout.razorpay.com', 'https://cdn.razorpay.com', 'https://connect.facebook.net', 'https://challenges.cloudflare.com', 'https://static.cloudflareinsights.com', 'https://*.posthog.com', posthog],
    'style-src': ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com'],
    'font-src': ["'self'", 'data:', 'https://fonts.gstatic.com'],
    'img-src': ["'self'", 'data:', 'blob:', 'https://d2ol7oe51mr4n9.cloudfront.net', 'https://www.facebook.com', 'https://*.supabase.co', 'https://*.razorpay.com'],
    'media-src': ["'self'", 'blob:', 'https://d8j0ntlcm91z4.cloudfront.net'],
    'connect-src': ["'self'", 'https://*.supabase.co', 'wss://*.supabase.co', supabase, supabase?.replace('https:', 'wss:'), 'https://*.razorpay.com', 'https://*.posthog.com', posthog, 'https://www.facebook.com', 'https://connect.facebook.net', 'https://cloudflareinsights.com', 'https://static.cloudflareinsights.com', isDev && 'ws://localhost:*', isDev && 'ws://127.0.0.1:*'],
    'frame-src': ['https://*.razorpay.com', 'https://challenges.cloudflare.com'],
    'worker-src': ["'self'", 'blob:'],
    'object-src': ["'none'"],
    'base-uri': ["'self'"],
    'form-action': ["'self'"],
    'frame-ancestors': ["'none'"],
  };
  return Object.entries(directives).map(([key, values]) => `${key} ${unique(values)}`).join('; ')
    + (isDev ? '' : '; upgrade-insecure-requests');
}
