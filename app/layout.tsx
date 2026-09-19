import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { TrackingProvider } from "@/components/analytics/TrackingScripts";
import { JsonLd } from "@/components/seo/JsonLd";
import { SiteFooter } from "@/components/SiteFooter";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Dhansetu Hub — Your Bridge to Better Money Decisions",
  description: "SmartBudget, Resume AI, PDF Studio, and PeopleDesk in one local-first, privacy-centric bundle.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <JsonLd />
        <TrackingProvider />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
