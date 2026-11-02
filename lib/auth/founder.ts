import { getCurrentAuthSession } from "@/lib/better-auth-session";

export async function requireFounder() {
  const session = await getCurrentAuthSession();
  if (!session?.user) return { user: null, allowed: false as const };
  const allowedIds = (process.env.FOUNDER_USER_IDS ?? "").split(",").map((value) => value.trim()).filter(Boolean);
  return { user: session.user, allowed: allowedIds.includes(session.user.id) as boolean };
}
