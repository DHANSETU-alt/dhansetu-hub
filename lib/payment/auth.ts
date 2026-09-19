import type { NextRequest } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { testMode } from "./test-store";

export async function authenticatedUser(request: NextRequest) {
  if (testMode()) {
    const id = request.headers.get("x-test-user-id");
    return id ? { id, email: `${id}@example.test` } : null;
  }
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return null;
  const supabase = createServerClient(url, key, {
    cookies: { getAll: () => request.cookies.getAll(), setAll: () => undefined },
  });
  const { data, error } = await supabase.auth.getUser();
  return error || !data.user ? null : { id: data.user.id, email: data.user.email ?? "" };
}
