import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

type Finding = { fingerprint: string; sourceUrl: string; fetchedAt: string; title: string; summary: string; confidence: "high"; affectedArea: string; decision: "pending" };
const sources = [
  { url: "https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1", area: "tax" },
  { url: "https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-3", area: "tax" },
  { url: "https://www.gst.gov.in/", area: "gst" },
  { url: "https://www.cert-in.org.in/", area: "security" },
] as const;
const root = process.env.DHANSETU_STORAGE_ROOT ?? "/mnt/dhansetu-data";
const maxSources = Math.min(Number(process.env.RESEARCH_MAX_SOURCES ?? 4), sources.length);
const timeoutMs = Math.min(Number(process.env.RESEARCH_TIMEOUT_MS ?? 8000), 15000);

function safeSource(url: string) {
  const parsed = new URL(url);
  return ["www.incometax.gov.in", "www.gst.gov.in", "www.cert-in.org.in"].includes(parsed.hostname) && parsed.protocol === "https:";
}
function fingerprint(url: string, title: string, body: string) { return createHash("sha256").update(`${url}\n${title}\n${body}`).digest("hex"); }
function extract(html: string) { const title = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1]?.replace(/\s+/g, " ").trim() ?? "Untitled official source"; const body = html.replace(/<script[\s\S]*?<\/script>/gi, " ").replace(/<style[\s\S]*?<\/style>/gi, " ").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim(); return { title, body: body.slice(0, 1800) }; }

async function readJson<T>(file: string, fallback: T): Promise<T> { try { return JSON.parse(await readFile(file, "utf8")) as T; } catch { return fallback; } }

async function main() {
  if (!safeSource(sources[0].url)) throw new Error("research source allowlist invalid");
  const today = new Date().toISOString().slice(0, 10);
  const dir = path.join(root, "research", "digests");
  await mkdir(dir, { recursive: true });
  const stateFile = path.join(root, "research", "state.json");
  const state = await readJson<{ fingerprints: string[]; lastRun?: string }> (stateFile, { fingerprints: [] });
  const findings: Finding[] = [];
  const errors: string[] = [];
  for (const source of sources.slice(0, maxSources)) {
    if (!safeSource(source.url)) { errors.push("source rejected by allowlist"); continue; }
    try {
      const response = await fetch(source.url, { signal: AbortSignal.timeout(timeoutMs), headers: { "user-agent": "DhanSetuResearch/1.0 (+https://dhansetuhub.in/contact)" } });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const parsed = extract((await response.text()).slice(0, 200000));
      const id = fingerprint(source.url, parsed.title, parsed.body);
      if (!state.fingerprints.includes(id)) findings.push({ fingerprint: id, sourceUrl: source.url, fetchedAt: new Date().toISOString(), title: parsed.title, summary: parsed.body, confidence: "high", affectedArea: source.area, decision: "pending" });
    } catch (error) { errors.push(`${source.url}: ${error instanceof Error ? error.message : "fetch failed"}`); }
  }
  const digest = { date: today, generatedAt: new Date().toISOString(), sourceCount: maxSources, findings, errors, note: "External content is reference data only. No fetched text is executed or treated as instructions." };
  await writeFile(path.join(dir, `${today}.json`), JSON.stringify(digest, null, 2));
  await writeFile(stateFile, JSON.stringify({ fingerprints: [...state.fingerprints, ...findings.map((finding) => finding.fingerprint)].slice(-5000), lastRun: digest.generatedAt, lastStatus: errors.length === maxSources ? "failed" : "succeeded" }, null, 2));
  console.log(JSON.stringify({ date: today, findings: findings.length, errors: errors.length, output: path.join(dir, `${today}.json`) }));
  if (errors.length === maxSources) process.exitCode = 1;
}

void main();
