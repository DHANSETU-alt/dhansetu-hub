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
  metadataBase: new URL("https://dhansetuhub.in"),
  title: "Dhansetu Hub — Your Bridge to Better Money Decisions",
  description: "A thoughtful home for your money, documents, and next big idea. Browser-based tools built for everyday India. Private by design, quietly powerful.",
  openGraph: {
    title: "Dhansetu Hub — Your Bridge to Better Money Decisions",
    description: "A thoughtful home for your money, documents, and next big idea. Browser-based tools built for everyday India. Private by design, quietly powerful.",
    url: "https://dhansetuhub.in",
    siteName: "Dhansetu Hub",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "Dhansetu Hub" }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Dhansetu Hub — Your Bridge to Better Money Decisions",
    description: "A thoughtful home for your money, documents, and next big idea. Browser-based tools built for everyday India. Private by design, quietly powerful.",
    images: ["/og-image.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..800&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Noto+Sans+Gujarati:wght@400;500;600;700&display=swap"
        />
      </head>
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
