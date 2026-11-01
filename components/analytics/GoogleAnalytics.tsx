"use client";

import Script from "next/script";

const measurementId = process.env.NEXT_PUBLIC_GA_ID;

export function GoogleAnalytics() {
  if (!measurementId) return null;
  return <>
    <Script src={`https://www.googletagmanager.com/gtag/js?id=${measurementId}`} strategy="afterInteractive" />
    <Script id="google-analytics" strategy="afterInteractive">
      {`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','${measurementId}',{anonymize_ip:true,allow_google_signals:false});`}
    </Script>
  </>;
}

export function trackDhanSetuEvent(event: string, parameters: Record<string, string | number | boolean> = {}) {
  if (typeof window === "undefined" || typeof window.gtag !== "function") return false;
  window.gtag("event", event, parameters);
  return true;
}

declare global {
  interface Window {
    dataLayer: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}
