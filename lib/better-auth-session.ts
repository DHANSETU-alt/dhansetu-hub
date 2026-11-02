import { headers } from "next/headers";
import type { NextRequest } from "next/server";
import { auth } from "@/lib/better-auth";

export async function getCurrentAuthSession() {
  return auth.api.getSession({ headers: await headers() });
}

export async function getRequestAuthSession(request: NextRequest) {
  return auth.api.getSession({ headers: request.headers });
}
