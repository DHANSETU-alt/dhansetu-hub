"use client";

// Real observed value, not a computed/fetched one -- ChatGPT Sites exposes no
// public API for its own usage-limit reset time. Read directly from the
// "Work usage" panel at chatgpt.com/sites (gear icon -> Usage) on 2026-08-30
// 16:17 IST, which showed "5-hour limit: resets in 1h 3m, 0% left". Update
// this constant by re-checking that panel if it goes stale.
const RESET_AT = "2026-08-30T11:51:00Z";

function formatRemaining(ms: number): string {
  if (ms <= 0) return "Ready now";
  const totalSeconds = Math.floor(ms / 1000);
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return `${h}h ${String(m).padStart(2, "0")}m ${String(s).padStart(2, "0")}s`;
}

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

export function ChatGptSitesCountdown() {
  const pathname = usePathname();
  const [remainingMs, setRemainingMs] = useState<number | null>(null);

  useEffect(() => {
    const target = new Date(RESET_AT).getTime();
    const tick = () => setRemainingMs(target - Date.now());
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  if (remainingMs === null || pathname?.startsWith("/concept3")) return null;
  const ready = remainingMs <= 0;

  return (
    <div
      className={`fixed top-0 left-0 right-0 z-50 flex items-center justify-between gap-3 px-4 py-2 text-sm border-b ${
        ready
          ? "bg-emerald-950/90 border-emerald-800 text-emerald-300"
          : "bg-amber-950/90 border-amber-900 text-amber-300"
      }`}
    >
      <span>
        ChatGPT Sites 5-hour usage limit —{" "}
        {ready ? "reset, safe to resume queued site edits" : "resets in"}
      </span>
      {!ready && <span className="font-mono tabular-nums">{formatRemaining(remainingMs)}</span>}
    </div>
  );
}
