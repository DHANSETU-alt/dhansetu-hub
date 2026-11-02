import { NextResponse } from "next/server";
import { PDFDocument } from "pdf-lib";

// pdf-lib uses the Node runtime reliably on Render's constrained builder.
export const runtime = "nodejs";

export async function POST(request: Request, { params }: { params: Promise<{ tool: string }> }) {
  const { tool } = await params;
  if (tool !== "merge") return NextResponse.json({ error: "This operation is browser-local or awaiting a verified worker.", tool }, { status: 501 });
  const form = await request.formData();
  const inputs = form.getAll("files").filter((value): value is File => value instanceof File);
  if (!inputs.length) return NextResponse.json({ error: "At least one PDF is required." }, { status: 400 });
  const output = await PDFDocument.create();
  for (const input of inputs) {
    const source = await PDFDocument.load(await input.arrayBuffer());
    const pages = await output.copyPages(source, source.getPageIndices());
    pages.forEach((page) => output.addPage(page));
  }
  const bytes = await output.save({ useObjectStreams: true });
  const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
  return new NextResponse(buffer, { headers: { "Content-Type": "application/pdf", "Content-Disposition": "attachment; filename=dhansetu-merged.pdf", "Cache-Control": "no-store" } });
}
