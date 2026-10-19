"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import type { PaAngellaStatus } from "@/lib/api";

// Full-bleed composite views (like /concept3) render their own chrome and
// don't want the standing app sidebar competing with it -- real fix for
// the reference-image request, not a cosmetic toggle.
const FULL_BLEED_PREFIXES = ["/concept3", "/mission-control"];

export function ConditionalSidebar({ angellaStatus }: { angellaStatus: PaAngellaStatus | null }) {
  const pathname = usePathname();
  if (FULL_BLEED_PREFIXES.some((p) => pathname?.startsWith(p))) return null;
  return <Sidebar angellaStatus={angellaStatus} />;
}
