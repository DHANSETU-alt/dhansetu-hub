import type { NextRequest } from "next/server";
import { testMode } from "./test-store";
import { getRequestAuthSession } from "@/lib/better-auth-session";

export async function authenticatedUser(request: NextRequest) {
  if (testMode()) {
    const id = request.headers.get("x-test-user-id");
    return id ? { id, email: `${id}@example.test` } : null;
  }
  const session = await getRequestAuthSession(request);
  return session?.user ? { id: session.user.id, email: session.user.email } : null;
}
