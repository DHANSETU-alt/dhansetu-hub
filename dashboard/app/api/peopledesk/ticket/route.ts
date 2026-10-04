import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  return NextResponse.json({ success: true, data: { id: "ticket_1" } }, { status: 201 });
}
