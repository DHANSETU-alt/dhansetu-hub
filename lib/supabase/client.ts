"use client";

import { createBrowserClient } from "@supabase/ssr";

export function createBrowserSupabase() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookieOptions: process.env.NEXT_PUBLIC_AUTH_COOKIE_DOMAIN
        ? { domain: process.env.NEXT_PUBLIC_AUTH_COOKIE_DOMAIN }
        : undefined,
    },
  );
}
