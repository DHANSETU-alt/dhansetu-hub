"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export function AutoRefresh({ intervalSeconds = 1 }: { intervalSeconds?: number }) {
  const router = useRouter();
  const [enabled, setEnabled] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<string>("");

  useEffect(() => {
    setLastRefresh(new Date().toLocaleTimeString());
  }, []);

  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(() => {
      router.refresh();
      setLastRefresh(new Date().toLocaleTimeString());
    }, intervalSeconds * 1000);
    return () => clearInterval(id);
  }, [enabled, intervalSeconds, router]);

  return (
    <div className="flex items-center gap-2 text-xs text-[var(--muted-foreground)]">
      <span suppressHydrationWarning>{lastRefresh && `updated ${lastRefresh}`}</span>
      <button
        onClick={() => setEnabled((e) => !e)}
        className={`rounded-full px-2 py-0.5 border ${
          enabled ? "border-[var(--local)] text-[var(--local)]" : "border-[var(--border)] text-[var(--muted-foreground)]"
        }`}
      >
        {enabled ? `live (${intervalSeconds}s)` : "paused"}
      </button>
      <button onClick={() => router.refresh()} className="rounded-full px-2 py-0.5 border border-[var(--border)] hover:text-[var(--ink)]">
        refresh now
      </button>
    </div>
  );
}
