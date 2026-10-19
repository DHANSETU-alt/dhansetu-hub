import { promises as fs } from "node:fs";
import path from "node:path";
import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Serverless-safe inventory endpoint. Source generation belongs in CI, not request handling.
export async function GET() {
  const root = path.join(process.cwd(), "portfolio");
  let files: string[] = [];
  try {
    files = (await fs.readdir(root, { withFileTypes: true }))
      .filter((entry) => entry.isFile() && !entry.name.startsWith("."))
      .map((entry) => entry.name).sort();
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
  return NextResponse.json({ status: "ok", files, generatedAt: new Date().toISOString() });
}
