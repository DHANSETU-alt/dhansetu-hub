import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ConditionalSidebar } from "@/components/ConditionalSidebar";
import { getPaAngellaStatus } from "@/lib/api";
import { ChatGptSitesCountdown } from "@/components/ChatGptSitesCountdown";
import { MatrixRain } from "@/components/AmbientEffects";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Shakthi AI OS — Control Center",
  description: "Founder-operable dashboard for the Shakthi AI OS multi-agent orchestration platform",
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const angellaStatus = await getPaAngellaStatus().catch(() => null);

  return (
    <html lang="en" className={`dark ${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full bg-[var(--bg)] text-[var(--ink)]">
        <div className="fixed inset-0 z-0" aria-hidden="true">
          <MatrixRain />
        </div>
        <ChatGptSitesCountdown />
        <div className="relative z-10 flex flex-col pt-9 md:flex-row">
          <ConditionalSidebar angellaStatus={angellaStatus} />
          <main className="flex-1 min-w-0 px-4 py-4 sm:px-6 md:px-8 md:py-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
