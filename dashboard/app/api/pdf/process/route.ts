import { NextRequest, NextResponse } from "next/server";
import { writeFile, mkdir, readFile } from "fs/promises";
import { randomUUID } from "crypto";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";

const execFileAsync = promisify(execFile);
// dashboard/ -> shakthi-os/ -- orchestrator's package root, so `python3 -m
// orchestrator.cli` resolves. Same requirement documented in README's
// "Web dashboard" section for the API server.
const PROJECT_ROOT = path.resolve(process.cwd(), "..");
const PDF_JOBS_DIR = path.join(PROJECT_ROOT, "pdf_studio_files", "jobs");

const VALID_OPERATIONS = ["merge", "split", "compress", "images-to-pdf", "rotate", "extract", "protect", "unprotect"];

async function runCli(args: string[]): Promise<Record<string, unknown>> {
  const { stdout } = await execFileAsync("python3", ["-m", "orchestrator.cli", ...args], { cwd: PROJECT_ROOT, timeout: 30_000 });
  return JSON.parse(stdout.trim());
}

export async function POST(req: NextRequest) {
  const formData = await req.formData();
  const operation = formData.get("operation") as string;
  const email = (formData.get("email") as string | null)?.trim().toLowerCase();
  const password = formData.get("password") as string | null;
  const degrees = formData.get("degrees") as string | null;
  const pages = formData.get("pages") as string | null;
  const files = formData.getAll("files") as File[];

  if (!VALID_OPERATIONS.includes(operation)) {
    return NextResponse.json({ error: `unknown operation: ${operation}` }, { status: 400 });
  }
  if (!email) {
    return NextResponse.json({ error: "email is required — used only to track your 10 free uses, never shared" }, { status: 400 });
  }
  if (!files.length) {
    return NextResponse.json({ error: "no files uploaded" }, { status: 400 });
  }

  // The real gate: orchestrator/pricing.py is the single source of truth for
  // free-tier/subscription state (same module the founder's CLI and the
  // blackboxOps_OS Pricing page both use) -- this route used to skip it
  // entirely, so PDF Studio was unrestricted for everyone. Not anymore.
  const access = await runCli(["--pricing-check", "--email", email, "--product", "pdf_studio"]);
  if (access.error) {
    return NextResponse.json({ error: access.error as string }, { status: 500 });
  }
  if (!access.allowed) {
    return NextResponse.json({
      error: `Free tier used up (10/10). ${access.label} is ₹${access.price_inr}/year to continue.`,
      requiresPayment: true,
    }, { status: 402 });
  }

  const jobId = randomUUID();
  const jobDir = path.join(PDF_JOBS_DIR, jobId);
  await mkdir(jobDir, { recursive: true });

  const inputPaths: string[] = [];
  for (const file of files) {
    const buf = Buffer.from(await file.arrayBuffer());
    const inputPath = path.join(jobDir, file.name);
    await writeFile(inputPath, buf);
    inputPaths.push(inputPath);
  }

  const isSplit = operation === "split";
  const outputPath = isSplit ? path.join(jobDir, "split_out") : path.join(jobDir, `output.pdf`);

  const args = ["-m", "orchestrator.cli", "--pdf-process", operation, "--pdf-output", outputPath];
  for (const p of inputPaths) args.push("--pdf-input", p);
  if (password) args.push("--pdf-password", password);
  if (degrees) args.push("--pdf-degrees", degrees);
  if (pages) args.push("--pdf-pages", pages);

  try {
    await execFileAsync("python3", args, { cwd: PROJECT_ROOT, timeout: 60_000 });
  } catch (e) {
    const err = e as { stderr?: string; message?: string };
    return NextResponse.json({ error: (err.stderr || err.message || "PDF processing failed").trim() }, { status: 422 });
  }

  const downloadPath = isSplit ? path.join(outputPath, "split_pages.zip") : outputPath;
  const contentType = isSplit ? "application/zip" : "application/pdf";
  const filename = isSplit ? "dhansetu_split_pages.zip" : `dhansetu_${operation}.pdf`;

  let data: Buffer;
  try {
    data = await readFile(downloadPath);
  } catch {
    return NextResponse.json({ error: "processing completed but the output file was not found" }, { status: 500 });
  }

  // Only counted against the free tier once the file actually exists --
  // a failed run above returned before this point and never consumed a use.
  const usage = await runCli(["--pricing-record-usage", "--email", email, "--product", "pdf_studio"]);
  const remaining = typeof access.remaining_free === "number" ? Math.max(0, access.remaining_free - 1) : null;

  return new NextResponse(new Uint8Array(data), {
    headers: {
      "Content-Type": contentType,
      "Content-Disposition": `attachment; filename="${filename}"`,
      "Content-Length": String(data.length),
      "X-PDF-Free-Remaining": remaining !== null ? String(remaining) : "unlimited",
      "X-PDF-Use-Count": String((usage as { use_count?: number }).use_count ?? ""),
    },
  });
}
