import { SHAKTHI_OS_VERSION } from "@/lib/version";

export function ChatGptSitesCountdown() {
  return (
    <div className="fixed top-0 left-0 right-0 z-50 border-b border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm text-[var(--muted-foreground)]">
      {SHAKTHI_OS_VERSION.osName} V{SHAKTHI_OS_VERSION.version} · Local workspace · External usage limits unverified
    </div>
  );
}
