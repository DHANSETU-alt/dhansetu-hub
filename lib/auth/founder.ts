import { createServerSupabase } from "@/lib/supabase/server";

export async function requireFounder() {
  const { data } = await createServerSupabase().auth.getUser();
  if (!data.user) return { user: null, allowed: false as const };
  const allowedIds = (process.env.FOUNDER_USER_IDS ?? "").split(",").map((value) => value.trim()).filter(Boolean);
  return { user: data.user, allowed: allowedIds.includes(data.user.id) as boolean };
}
