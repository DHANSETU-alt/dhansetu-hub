import { lookup } from "node:dns/promises";
import * as cheerio from "cheerio";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MAX_HTML_BYTES = 1_500_000;
const MAX_INTERNAL_LINKS = 40;
const REQUEST_TIMEOUT_MS = 10_000;

type Severity = "high" | "medium" | "low";
type Finding = {
  id: string;
  title: string;
  detail: string;
  fix: string;
  severity: Severity;
  points: number;
};
type Check = Finding & { passed: boolean };

const headers = {
  "cache-control": "no-store",
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "POST, OPTIONS",
  "access-control-allow-headers": "content-type",
};

function json(data: unknown, status = 200) {
  return NextResponse.json(data, { status, headers });
}

function isPrivateAddress(address: string) {
  const normalized = address.toLowerCase();
  if (normalized === "::1" || normalized === "localhost" || normalized.endsWith(".localhost")) return true;
  if (normalized.startsWith("127.") || normalized.startsWith("10.") || normalized.startsWith("192.168.")) return true;
  const first = Number(normalized.split(".")[0]);
  const second = Number(normalized.split(".")[1]);
  if (first === 172 && second >= 16 && second <= 31) return true;
  if (normalized.startsWith("169.254.")) return true;
  return normalized.startsWith("fc") || normalized.startsWith("fd") || normalized.startsWith("fe80:");
}

async function assertPublicUrl(value: URL) {
  if (!/^https?:$/.test(value.protocol) || value.username || value.password || isPrivateAddress(value.hostname)) {
    throw new Error("Only public HTTP or HTTPS URLs are supported.");
  }
  const records = await lookup(value.hostname, { all: true, verbatim: true });
  if (!records.length || records.some((record) => isPrivateAddress(record.address))) {
    throw new Error("The target resolves to a private or unavailable address.");
  }
}

async function readLimitedText(response: Response) {
  if (!response.body) return "";
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  while (true) {
    const next = await reader.read();
    if (next.done) break;
    total += next.value.byteLength;
    if (total > MAX_HTML_BYTES) {
      await reader.cancel();
      throw new Error("The page is larger than the supported 1.5 MB audit limit.");
    }
    chunks.push(next.value);
  }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder().decode(bytes);
}

async function publicFetch(input: URL, init: RequestInit = {}) {
  let current = new URL(input.toString());
  for (let redirects = 0; redirects <= 3; redirects += 1) {
    await assertPublicUrl(current);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      const response = await fetch(current, {
        ...init,
        redirect: "manual",
        signal: controller.signal,
        headers: { "user-agent": "DhanSetuHub-SEO-Audit/1.0 (passive; public evidence)", ...(init.headers || {}) },
      });
      if (![301, 302, 303, 307, 308].includes(response.status)) return { response, url: current };
      const location = response.headers.get("location");
      if (!location) return { response, url: current };
      current = new URL(location, current);
    } finally {
      clearTimeout(timeout);
    }
  }
  throw new Error("The target redirected too many times.");
}

function check(input: Omit<Check, "passed"> & { passed: boolean }): Check {
  return input;
}

function issueFrom(item: Check): Finding | null {
  return item.passed ? null : item;
}

async function statusFor(url: URL) {
  try {
    const result = await publicFetch(url, { method: "HEAD" });
    return result.response.status;
  } catch {
    return 0;
  }
}

async function inspectInternalLinks($: cheerio.CheerioAPI, origin: URL) {
  const links = Array.from(new Set(
    $("a[href]").toArray().map((element) => $(element).attr("href") || "").map((href) => {
      try { return new URL(href, origin); } catch { return null; }
    }).filter((url): url is URL => Boolean(url && url.origin === origin.origin && /^https?:$/.test(url.protocol) && !url.hash)),
  )).slice(0, MAX_INTERNAL_LINKS);
  const failures: string[] = [];
  for (let index = 0; index < links.length; index += 5) {
    const group = links.slice(index, index + 5);
    const results = await Promise.all(group.map(async (url) => ({ url, status: await statusFor(url) })));
    results.forEach(({ url, status }) => {
      if (status === 0 || status >= 400) failures.push(`${url.pathname} (${status || "unreachable"})`);
    });
  }
  return { checked: links.length, failures };
}

async function audit(target: URL) {
  const started = Date.now();
  const { response, url: finalUrl } = await publicFetch(target);
  const html = await readLimitedText(response);
  const $ = cheerio.load(html);
  const title = $("title").first().text().trim();
  const description = $("meta[name='description']").attr("content")?.trim() || "";
  const h1Count = $("h1").length;
  const headings = $("h1,h2,h3,h4,h5,h6").toArray().map((element) => Number(element.tagName.slice(1)));
  const hasHeadingSkip = headings.some((level, index) => index > 0 && level > headings[index - 1] + 1);
  const canonical = $("link[rel='canonical']").attr("href") || "";
  const ogRequired = ["og:title", "og:description", "og:image"];
  const missingOg = ogRequired.filter((property) => !$("meta[property='" + property + "']").attr("content"));
  const images = $("img").toArray();
  const missingAlt = images.filter((element) => !($(element).attr("alt") || "").trim()).length;
  const internal = await inspectInternalLinks($, finalUrl);
  const robotsStatus = await statusFor(new URL("/robots.txt", finalUrl));
  const sitemapStatus = await statusFor(new URL("/sitemap.xml", finalUrl));
  const responseTimeMs = Date.now() - started;

  const checks: Check[] = [
    check({ id: "title", title: "Title tag", passed: Boolean(title) && title.length >= 50 && title.length <= 60, severity: "high", points: 12, detail: title ? `${title.length} characters found.` : "No title tag found.", fix: "Add one clear title between 50 and 60 characters." }),
    check({ id: "description", title: "Meta description", passed: Boolean(description) && description.length >= 120 && description.length <= 160, severity: "high", points: 12, detail: description ? `${description.length} characters found.` : "No meta description found.", fix: "Add a useful description between 120 and 160 characters." }),
    check({ id: "h1", title: "Single H1", passed: h1Count === 1, severity: "high", points: 12, detail: `${h1Count} H1 element${h1Count === 1 ? "" : "s"} found.`, fix: "Use exactly one descriptive H1 for the page topic." }),
    check({ id: "heading-structure", title: "Heading structure", passed: headings.length > 0 && !hasHeadingSkip, severity: "medium", points: 8, detail: headings.length ? (hasHeadingSkip ? "Heading levels skip a rank." : `${headings.length} headings follow a usable hierarchy.`) : "No headings found.", fix: "Keep heading levels in order so sections are easy to navigate." }),
    check({ id: "canonical", title: "Canonical URL", passed: Boolean(canonical), severity: "medium", points: 8, detail: canonical || "No canonical link found.", fix: "Add a canonical link for the preferred URL." }),
    check({ id: "open-graph", title: "OpenGraph preview", passed: missingOg.length === 0, severity: "low", points: 6, detail: missingOg.length ? `Missing ${missingOg.join(", ")}.` : "Title, description, and image tags found.", fix: "Add the missing social preview tags." }),
    check({ id: "image-alt", title: "Image alt text", passed: missingAlt === 0, severity: "medium", points: 10, detail: images.length ? `${images.length - missingAlt}/${images.length} images have alt text.` : "No images found.", fix: "Describe meaningful images with concise alt text." }),
    check({ id: "robots", title: "Robots.txt", passed: robotsStatus >= 200 && robotsStatus < 400, severity: "low", points: 5, detail: robotsStatus ? `robots.txt returned HTTP ${robotsStatus}.` : "robots.txt was unavailable.", fix: "Publish a readable robots.txt at the domain root." }),
    check({ id: "sitemap", title: "Sitemap.xml", passed: sitemapStatus >= 200 && sitemapStatus < 400, severity: "low", points: 5, detail: sitemapStatus ? `sitemap.xml returned HTTP ${sitemapStatus}.` : "sitemap.xml was unavailable.", fix: "Publish an XML sitemap and reference it from robots.txt." }),
    check({ id: "internal-links", title: "Internal links", passed: internal.failures.length === 0, severity: "medium", points: 10, detail: `${internal.checked} internal links checked${internal.failures.length ? `; ${internal.failures.length} need attention.` : "."}`, fix: internal.failures.length ? `Review: ${internal.failures.slice(0, 4).join(", ")}` : "Keep internal navigation returning successful responses." }),
    check({ id: "page-speed", title: "Initial response speed", passed: responseTimeMs <= 1500, severity: "low", points: 6, detail: `Initial document response completed in ${responseTimeMs} ms.`, fix: "Reduce server work, compress HTML, and use caching where appropriate." }),
  ];

  const total = checks.reduce((sum, item) => sum + item.points, 0);
  const earned = checks.filter((item) => item.passed).reduce((sum, item) => sum + item.points, 0);
  const issues = checks.map(issueFrom).filter((item): item is Finding => Boolean(item));
  const passed = checks.filter((item) => item.passed).map(({ id, title: itemTitle, detail, points }) => ({ id, title: itemTitle, detail, points }));
  return {
    score: Math.round((earned / total) * 100),
    issues,
    passed,
    meta: {
      requestedUrl: target.toString(), finalUrl: finalUrl.toString(), responseStatus: response.status,
      responseTimeMs, checks: checks.length, issueCount: issues.length, passedCount: passed.length,
      linksChecked: internal.checked, generatedAt: new Date().toISOString(), source: "public-passive-evidence",
    },
  };
}

export async function OPTIONS() { return new NextResponse(null, { status: 204, headers }); }

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const raw = String(body?.url || "").trim();
    const target = new URL(raw);
    await assertPublicUrl(target);
    return json(await audit(target));
  } catch (error) {
    const message = error instanceof Error ? error.message : "The SEO audit could not read that public URL.";
    return json({ error: message }, message.includes("Only public") || message.includes("private") ? 422 : 502);
  }
}
