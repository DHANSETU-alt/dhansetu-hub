import { NextRequest, NextResponse } from "next/server";
import { authenticatedUser } from "@/lib/payment/auth";
import { purchasesForUser } from "@/lib/payment/records";

export async function GET(request: NextRequest) {
  const user = await authenticatedUser(request);
  if (!user) return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  return NextResponse.json({ purchases: await purchasesForUser(user.id) });
}
