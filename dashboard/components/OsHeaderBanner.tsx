"use client";

import { MatrixRain } from "@/components/AmbientEffects";
import { SHAKTHI_OS_VERSION } from "@/lib/version";

// Real, visible matrix-rain banner strip -- deliberately its own isolated
// canvas + fixed height, so the rain is dense and obviously visible right
// under the top bar, instead of fighting dense card content below it.
export function OsHeaderBanner() {
  return (
    <div className="relative h-16 overflow-hidden border-b border-[var(--border)] bg-[#020303]">
      <div className="absolute inset-0">
        <MatrixRain />
      </div>
      <div className="relative z-10 h-full flex items-center justify-center px-6">
        <div className="text-center">
          <div className="text-[13px] tracking-[0.25em] font-semibold text-[var(--ink)] font-mono-num">
            {SHAKTHI_OS_VERSION.osName}
            <span className="text-emerald-400 ml-2">v{SHAKTHI_OS_VERSION.version}</span>
          </div>
          <div className="text-[10px] tracking-[0.3em] uppercase text-[var(--muted-foreground)] mt-0.5">
            {SHAKTHI_OS_VERSION.codename} &bull; Intelligent. Autonomous. Accountable.
          </div>
        </div>
      </div>
    </div>
  );
}
