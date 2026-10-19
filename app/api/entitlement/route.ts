import { NextRequest, NextResponse } from "next/server";
import { authenticatedUser } from "@/lib/payment/auth";
import { hasEntitlement } from "@/lib/payment/entitlement";

export async function GET(request: NextRequest) {
  const user = await authenticatedUser(request);
  if (!user) return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  return NextResponse.json({ active: await hasEntitlement(user.id), appUrl: process.env.NEXT_PUBLIC_APP_URL ?? "https://budget.dhansetuhub.in" });
}
