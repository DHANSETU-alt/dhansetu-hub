"use client";

import { useState } from "react";
import type { WatchedWebsite, WebsiteIncident } from "@/lib/api";

// Deliberately NOT the shared @/components/ui theme -- founder asked for a
// distinct "serious cyber command center" look: near-black, neon
// green/cyan only (a muted neon red is added for offline/alert states --
// pure green/cyan can't communicate danger, and a monitoring tool that
// can't show danger clearly would be a real usability regression, not a
// style purity win), monospace, sharp corners, dense.
const NEON_GREEN = "#39ff14";
const NEON_CYAN = "#22ffe6";
const NEON_RED = "#ff2b4d";
const NEON_AMBER = "#ffb020";
const BG = "#050807";
const PANEL_BG = "#0a0f0d";
const BORDER = "#123028";

const MONO = "var(--font-geist-mono), ui-monospace, SFMono-Regular, Menlo, monospace";

function statusColor(status: string | undefined) {
  if (status === "online") return NEON_GREEN;
  if (status === "offline") return NEON_RED;
  return "#3a4a44";
}

function fmtMs(ms: number | null) {
  if (ms === null) return "--";
  return `${ms}ms`;
}

function fmtAgo(iso: string | null) {
  if (!iso) return "never";
  const t = new Date(iso.includes("T") ? iso : iso.replace(" ", "T") + "Z").getTime();
  const s = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

export function WebsiteHealthWatcher({
  initialSites,
  initialIncidents,
}: {
  initialSites: WatchedWebsite[];
  initialIncidents: WebsiteIncident[];
}) {
  const [sites, setSites] = useState(initialSites);
  const [incidents, setIncidents] = useState(initialIncidents);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);

  const [refreshError, setRefreshError] = useState<string | null>(null);

  async function runRefresh() {
    setRefreshing(true);
    setRefreshError(null);
    try {
      // Same-origin proxy (app/api/website-health/refresh/route.ts), not a
      // direct browser->127.0.0.1:8787 fetch -- Chrome's Private Network
      // Access preflight kills that (confirmed live: the Python API's
      // stdlib http.server has no OPTIONS handler, real 501 on preflight).
      const res = await fetch("/api/website-health/refresh", { cache: "no-store" });
      const data = await res.json();
      if (!res.ok || data.error) {
        setRefreshError(data.error || `refresh failed (${res.status})`);
        return;
      }
      setSites(data.sites);
      setIncidents(data.incidents);
      setLastRefresh(new Date().toLocaleTimeString());
    } catch (e) {
      setRefreshError(e instanceof Error ? e.message : "refresh failed");
    } finally {
      setRefreshing(false);
    }
  }

  const onlineCount = sites.filter((s) => s.latest_check?.status === "online").length;
  const alertCount = sites.filter((s) => s.in_alert).length;
  const openIncidents = incidents.filter((i) => i.status === "open");

  return (
    <div
      className="min-h-screen -m-6 p-6 relative overflow-hidden"
      style={{ background: BG, color: NEON_GREEN, fontFamily: MONO }}
    >
      {/* scanline texture */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: "repeating-linear-gradient(0deg, #fff 0px, #fff 1px, transparent 1px, transparent 3px)",
        }}
      />

      <div className="relative space-y-5">
        <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: BORDER }}>
          <div>
            <h1
              className="text-lg tracking-widest uppercase font-bold"
              style={{ color: NEON_CYAN, textShadow: `0 0 8px ${NEON_CYAN}66` }}
            >
              &gt; BLACKBOXOPS_OS :: WEBSITE HEALTH WATCHER
            </h1>
            <p className="text-[11px] mt-1 opacity-60">
              real HTTP + TLS handshake checks -- background scan every 300s, manual refresh below
            </p>
          </div>
          <button
            onClick={runRefresh}
            disabled={refreshing}
            className="px-4 py-2 text-xs uppercase tracking-wider font-bold border transition-colors"
            style={{
              borderColor: NEON_CYAN,
              color: refreshing ? "#0a1a17" : NEON_CYAN,
              background: refreshing ? NEON_CYAN : "transparent",
              boxShadow: refreshing ? "none" : `0 0 10px ${NEON_CYAN}33`,
            }}
          >
            {refreshing ? "SCANNING..." : "[ REFRESH NOW ]"}
          </button>
        </div>

        {lastRefresh && !refreshError && (
          <div className="text-[11px]" style={{ color: NEON_CYAN }}>
            last manual refresh: {lastRefresh}
          </div>
        )}
        {refreshError && (
          <div className="text-[11px]" style={{ color: NEON_RED }}>
            refresh failed: {refreshError}
          </div>
        )}

        {/* stat strip */}
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "SITES WATCHED", value: sites.length, color: NEON_CYAN },
            { label: "ONLINE", value: `${onlineCount}/${sites.length}`, color: NEON_GREEN },
            { label: "IN ALERT", value: alertCount, color: alertCount > 0 ? NEON_RED : NEON_GREEN },
            { label: "OPEN INCIDENTS", value: openIncidents.length, color: openIncidents.length > 0 ? NEON_RED : NEON_GREEN },
          ].map((s) => (
            <div key={s.label} className="p-3 border" style={{ borderColor: BORDER, background: PANEL_BG }}>
              <div className="text-[10px] opacity-50 tracking-widest">{s.label}</div>
              <div className="text-2xl font-bold mt-1" style={{ color: s.color }}>{s.value}</div>
            </div>
          ))}
        </div>

        {/* site grid */}
        <div className="border" style={{ borderColor: BORDER, background: PANEL_BG }}>
          <div
            className="grid text-[10px] uppercase tracking-widest px-3 py-2 border-b opacity-60"
            style={{ borderColor: BORDER, gridTemplateColumns: "24px 2fr 90px 90px 100px 110px 60px" }}
          >
            <div></div>
            <div>Site</div>
            <div>Status</div>
            <div>Response</div>
            <div>SSL Expiry</div>
            <div>Last Checked</div>
            <div>Alert</div>
          </div>
          {sites.map((s) => {
            const lc = s.latest_check;
            const color = statusColor(lc?.status);
            return (
              <div
                key={s.id}
                className="grid items-center px-3 py-2.5 text-xs border-b last:border-b-0"
                style={{ borderColor: BORDER, gridTemplateColumns: "24px 2fr 90px 90px 100px 110px 60px" }}
              >
                <div className="flex justify-center">
                  <span
                    className="inline-block w-2 h-2 rounded-full animate-pulse"
                    style={{ background: color, boxShadow: `0 0 6px ${color}` }}
                  />
                </div>
                <div>
                  <div style={{ color: NEON_CYAN }}>{s.label}</div>
                  <div className="opacity-40 text-[10px]">{s.url}</div>
                  {lc?.error_detail && <div className="text-[10px] mt-0.5" style={{ color: NEON_RED }}>{lc.error_detail}</div>}
                </div>
                <div style={{ color }} className="uppercase font-bold">{lc?.status ?? "UNKNOWN"}</div>
                <div style={{ color: (lc?.response_time_ms ?? 0) > s.alert_response_ms_threshold ? NEON_AMBER : NEON_GREEN }}>
                  {fmtMs(lc?.response_time_ms ?? null)}
                </div>
                <div className="opacity-80">
                  {lc?.ssl_days_remaining !== null && lc?.ssl_days_remaining !== undefined
                    ? `${lc.ssl_days_remaining}d`
                    : "--"}
                </div>
                <div className="opacity-60" suppressHydrationWarning>{fmtAgo(lc?.checked_at ?? null)}</div>
                <div>
                  {s.in_alert ? (
                    <span className="px-1.5 py-0.5 text-[10px] font-bold" style={{ color: "#000", background: NEON_RED }}>
                      ALERT
                    </span>
                  ) : (
                    <span className="opacity-30 text-[10px]">--</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* incident log */}
        <div className="border" style={{ borderColor: BORDER, background: PANEL_BG }}>
          <div className="text-[10px] uppercase tracking-widest px-3 py-2 border-b opacity-60" style={{ borderColor: BORDER }}>
            Incident Log
          </div>
          {incidents.length === 0 ? (
            <div className="px-3 py-4 text-xs opacity-40">no incidents recorded</div>
          ) : (
            incidents.map((inc) => (
              <div
                key={inc.id}
                className="flex items-center justify-between px-3 py-2 text-xs border-b last:border-b-0"
                style={{ borderColor: BORDER }}
              >
                <div className="flex items-center gap-3">
                  <span
                    className="text-[10px] font-bold px-1.5 py-0.5"
                    style={{
                      color: inc.status === "open" ? "#000" : NEON_GREEN,
                      background: inc.status === "open" ? NEON_RED : "transparent",
                      border: inc.status === "open" ? "none" : `1px solid ${NEON_GREEN}`,
                    }}
                  >
                    {inc.status.toUpperCase()}
                  </span>
                  <span style={{ color: NEON_CYAN }}>{inc.website_label}</span>
                  <span className="opacity-50">{inc.summary}</span>
                </div>
                <div className="opacity-40 text-[10px]" suppressHydrationWarning>
                  opened {fmtAgo(inc.opened_at)}
                  {inc.closed_at ? ` -- closed ${fmtAgo(inc.closed_at)}` : ""}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
