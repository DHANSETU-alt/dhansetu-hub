import { NextResponse, type NextRequest } from "next/server";

export async function GET(request: NextRequest) {
  const next = request.nextUrl.searchParams.get("next");
  const destination = next?.startsWith("/") && !next.startsWith("//") ? next : "/";
  return NextResponse.redirect(new URL(`/login?error=legacy_auth_callback&next=${encodeURIComponent(destination)}`, request.url));
}
