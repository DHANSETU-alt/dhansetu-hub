import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";

const execFileAsync = promisify(execFile);
const PROJECT_ROOT = path.resolve(process.cwd(), "..");

// Stage 1 (Business Discovery) ONLY -- see orchestrator/onboarding.py's
// own docstring. Field list kept in one place there
// (onboarding.INTAKE_FIELDS); this route just forwards whatever the form
// posts under those same keys, so adding a field is a Python-side change,
// not a two-place edit.
const FIELD_KEYS = [
  "business_name", "industry", "website", "business_model", "target_customer",
  "revenue_streams", "team_size", "monthly_revenue_range", "main_challenges",
  "preferred_tools", "current_software", "growth_goal_12mo",
];

export async function POST(req: NextRequest) {
  const body = await req.json();
  if (!body.business_name || !String(body.business_name).trim()) {
    return NextResponse.json({ error: "business_name is required" }, { status: 400 });
  }

  const startArgs = ["-m", "orchestrator.cli", "--discovery-start"];
  for (const key of FIELD_KEYS) {
    const val = body[key];
    if (val && String(val).trim()) {
      startArgs.push(`--discovery-${key.replace(/_/g, "-")}`, String(val));
    }
  }

  let discoveryId: number;
  try {
    const { stdout } = await execFileAsync("python3", startArgs, { cwd: PROJECT_ROOT, timeout: 20_000 });
    const started = JSON.parse(stdout.trim().split("\n").pop() || "{}");
    if (started.error) return NextResponse.json(started, { status: 400 });
    discoveryId = started.discovery_id;
  } catch (e) {
    const err = e as { stderr?: string; message?: string };
    return NextResponse.json({ error: (err.stderr || err.message || "Intake failed").trim() }, { status: 422 });
  }

  // Real analysis call -- a real local-model task, can take a while under
  // load, so give it real headroom rather than the 20s used for the
  // (purely deterministic) intake write above.
  try {
    const { stdout } = await execFileAsync(
      "python3", ["-m", "orchestrator.cli", "--discovery-analyze", String(discoveryId)],
      { cwd: PROJECT_ROOT, timeout: 110_000 }
    );
    const analyzed = JSON.parse(stdout.trim().split("\n").pop() || "{}");
    return NextResponse.json(analyzed);
  } catch (e) {
    const err = e as { stderr?: string; message?: string };
    // Intake itself succeeded and is saved -- only the analysis step
    // failed/timed out, so say so specifically rather than a bare error.
    return NextResponse.json(
      { discovery_id: discoveryId, error: "Intake saved, but analysis failed or timed out: " + (err.stderr || err.message || "unknown") },
      { status: 202 }
    );
  }
}
