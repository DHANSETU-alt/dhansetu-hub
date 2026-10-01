import { NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";

// Real, file-backed status for the SHAKTHI_OS v5.1 Agent Control panel.
// Every field here is read from a real file on disk at request time --
// nothing is hardcoded as a fabricated number. Where a value genuinely
// can't be derived without guessing, it's returned as null and the client
// renders "not yet tracked" rather than inventing a plausible figure --
// per the founder's own explicit v5.1 "no fake status" rule.

const REPO_ROOT = path.join(process.cwd(), ".."); // dashboard/ -> shakthi-os/
const WATCHDOG_PATH = path.join(REPO_ROOT, "docs", "v3.4", "TASK_1_WATCHDOG_STATUS.md");
const FAILURE_MEMORY_PATH = path.join(REPO_ROOT, "data", "failure-memory.json");

// Task 1 acceptance checklist, assessed 2026-09-13 directly against the
// real contents of TASK_1_WATCHDOG_STATUS.md / TASK_1_MARKETING_KIT.md /
// TASK_1_DELIVERY_SOP.md / TASK_1_CUSTOMER_TRACKER.md (all in docs/v3.4/)
// -- this is a real assessment recorded here, not computed by parsing
// those docs at request time (their prose doesn't have a machine-checkable
// per-item status marker). Update this list by hand when a criterion's
// real status changes -- do not silently increment the count.
const TASK1_CRITERIA: { item: string; done: boolean; evidence: string }[] = [
  { item: "Product page", done: true, evidence: "dhansetuhub.in homepage live" },
  { item: "Clear pricing", done: true, evidence: "Free/₹149/₹399 live, curl-verified zero leftover ₹99" },
  { item: "LeakShield explanation", done: true, evidence: "real detection engine + copy, lib/leakshield.ts" },
  { item: "Lead CTA", done: true, evidence: "homepage CTAs" },
  { item: "Lead form", done: true, evidence: "JoinForm -> /api/waitlist, real D1 table" },
  { item: "Thank-you / next-step flow", done: true, evidence: "Razorpay success modal" },
  { item: "Marketing kit", done: true, evidence: "docs/v3.4/TASK_1_MARKETING_KIT.md" },
  { item: "Gujarati pitch", done: true, evidence: "included in TASK_1_MARKETING_KIT.md" },
  { item: "Delivery SOP", done: true, evidence: "docs/v3.4/TASK_1_DELIVERY_SOP.md" },
  { item: "Customer tracker", done: true, evidence: "docs/v3.4/TASK_1_CUSTOMER_TRACKER.md (seeded, no real leads logged yet)" },
  { item: "Watchdog status doc", done: true, evidence: "docs/v3.4/TASK_1_WATCHDOG_STATUS.md" },
  { item: "Build passes", done: true, evidence: "npm run build/lint/test all pass on task1-leakshield @ e216a2a" },
];

function extractSection(md: string, heading: string): string | null {
  const re = new RegExp(`##\\s*${heading}\\s*\\n([\\s\\S]*?)(?=\\n##\\s|$)`, "i");
  const m = md.match(re);
  return m ? m[1].trim() : null;
}

export async function GET() {
  let watchdogRaw: string | null = null;
  let watchdogError: string | null = null;
  try {
    watchdogRaw = fs.readFileSync(WATCHDOG_PATH, "utf-8");
  } catch (e) {
    watchdogError = e instanceof Error ? e.message : "could not read TASK_1_WATCHDOG_STATUS.md";
  }

  let failureMemoryCount: number | null = null;
  let failureMemoryError: string | null = null;
  try {
    const raw = fs.readFileSync(FAILURE_MEMORY_PATH, "utf-8");
    const parsed = JSON.parse(raw);
    failureMemoryCount = typeof parsed.count === "number" ? parsed.count : Array.isArray(parsed.entries) ? parsed.entries.length : null;
  } catch (e) {
    failureMemoryError = e instanceof Error ? e.message : "could not read data/failure-memory.json";
  }

  const topBlockerSection = watchdogRaw ? extractSection(watchdogRaw, "Top blocker") : null;
  // First blocker line only (the doc numbers #1/#2) -- the panel shows the
  // single most urgent one, the full doc has both.
  const topBlocker = topBlockerSection
    ? topBlockerSection.split(/\n\n/)[0].replace(/\*\*/g, "").trim()
    : null;

  const buildTestSection = watchdogRaw ? extractSection(watchdogRaw, "Build/test result") : null;
  const buildTestStatus = buildTestSection
    ? (/\*\*fail/i.test(buildTestSection) ? "fail" : /\*\*pass\*\*/i.test(buildTestSection) ? "pass" : "unknown")
    : null;

  const done = TASK1_CRITERIA.filter((c) => c.done).length;
  const total = TASK1_CRITERIA.length;

  return NextResponse.json({
    mode: "Operator Mode — Task 1",
    activeTask: "Task 1 — DhanSetu Budget Tracker + LeakShield (dhansetuhub.in)",
    topBlocker: topBlocker ?? (watchdogError ? `not tracked: ${watchdogError}` : "not yet tracked"),
    buildTestStatus: buildTestStatus ?? "not yet tracked",
    failureMemoryCount: failureMemoryCount,
    failureMemoryError,
    readiness: { done, total, percent: Math.round((done / total) * 100), criteria: TASK1_CRITERIA },
    source: {
      watchdog: watchdogError ? null : WATCHDOG_PATH,
      failureMemory: failureMemoryError ? null : FAILURE_MEMORY_PATH,
    },
  });
}
