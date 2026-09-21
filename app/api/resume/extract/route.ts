import { NextRequest, NextResponse } from "next/server";
import { authenticatedUser } from "@/lib/payment/auth";
import { hasEntitlement } from "@/lib/payment/entitlement";
import { isSupportedResume, keywordGaps, MAX_RESUME_BYTES, normalizeResumeText } from "@/lib/resume/extract";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const user = await authenticatedUser(request);
  if (!user) return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  if (!(await hasEntitlement(user.id))) return NextResponse.json({ error: "An active DhanSetu plan is required" }, { status: 403 });

  const contentLength = Number(request.headers.get("content-length") ?? 0);
  if (contentLength > MAX_RESUME_BYTES + 200_000) return NextResponse.json({ error: "Resume must be 5 MB or smaller" }, { status: 413 });

  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return NextResponse.json({ error: "Could not read upload" }, { status: 400 });
  }
  const file = form.get("resume");
  const jobDescription = typeof form.get("jobDescription") === "string" ? String(form.get("jobDescription")).slice(0, 10_000) : "";
  if (!(file instanceof File)) return NextResponse.json({ error: "Choose a PDF or DOCX resume" }, { status: 400 });
  if (file.size > MAX_RESUME_BYTES) return NextResponse.json({ error: "Resume must be 5 MB or smaller" }, { status: 413 });
  if (!isSupportedResume(file.name, file.type)) return NextResponse.json({ error: "Only PDF and DOCX resumes are supported" }, { status: 415 });

  const buffer = Buffer.from(await file.arrayBuffer());
  let text: string;
  try {
    if (file.name.toLowerCase().endsWith(".docx")) {
      const mammoth = (await import("mammoth")).default;
      text = (await mammoth.extractRawText({ buffer })).value;
    } else {
      const { PDFParse } = await import("pdf-parse");
      const parser = new PDFParse({ data: new Uint8Array(buffer) });
      try {
        text = (await parser.getText()).text;
      } finally {
        await parser.destroy();
      }
    }
  } catch {
    return NextResponse.json({ error: "The file could not be extracted. Scanned or password-protected PDFs may need OCR or unlocking first." }, { status: 422 });
  }

  const normalized = normalizeResumeText(text);
  if (!normalized) return NextResponse.json({ error: "No readable text was found in this file" }, { status: 422 });
  return NextResponse.json({ text: normalized, keywordGaps: keywordGaps(normalized, jobDescription), persisted: false });
}
