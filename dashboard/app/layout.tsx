import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { getPaAngellaStatus } from "@/lib/api";

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
        <div className="flex">
          <Sidebar angellaStatus={angellaStatus} />
          <main className="flex-1 min-w-0 px-8 py-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
