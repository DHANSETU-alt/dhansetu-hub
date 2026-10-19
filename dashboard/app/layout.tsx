import type { Metadata } from "next";
import "./globals.css";
import { ConditionalSidebar } from "@/components/ConditionalSidebar";
import { getPaAngellaStatus } from "@/lib/api";
import { ChatGptSitesCountdown } from "@/components/ChatGptSitesCountdown";
import { OsHeaderBanner } from "@/components/OsHeaderBanner";

export const metadata: Metadata = {
  title: "Shakthi AI OS — Control Center",
  description: "Founder-operable dashboard for the Shakthi AI OS multi-agent orchestration platform",
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const angellaStatus = await getPaAngellaStatus().catch(() => null);

  return (
    <html lang="en" className="dark h-full antialiased">
      <body className="min-h-full bg-[var(--bg)] text-[var(--ink)]">
        {/* Real founder-facing complaint, 2026-09-13: "too mixtured" --
            LivingSystemBackground (matrix rain + 140-firefly swarm +
            radar sweep + ripples) was mounted here for EVERY dashboard
            page, competing with real CPU/RAM/revenue data tiles for
            attention on a screen meant to be scanned quickly, not admired.
            That heavy atmosphere is right for a customer-facing marketing
            page (see app/blackboxops-os/page.tsx, which renders its own
            copy directly and is unaffected by removing it here) -- wrong
            for a working control center. Removed from the shared layout;
            not deleted, since the one real customer-facing page that
            wants it still has its own mount. */}
        <ChatGptSitesCountdown />
        {/* mt-20 (80px), not the old pt-9 (36px): the countdown bar above
            is `fixed`, and its real rendered height is ~63px once its text
            wraps to two lines -- 36px clearance left OsHeaderBanner's title
            hidden underneath it. 80px clears that with room for narrower
            viewports wrapping to a third line. */}
        <div className="relative z-10 mt-20">
          <OsHeaderBanner />
        </div>
        <div className="relative z-10 flex flex-col md:flex-row">
          <ConditionalSidebar angellaStatus={angellaStatus} />
          <main className="flex-1 min-w-0 px-4 py-4 sm:px-6 md:px-8 md:py-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
