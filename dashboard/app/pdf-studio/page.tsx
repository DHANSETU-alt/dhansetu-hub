import { Card, CardHeader, CardBody, ComingSoon } from "@/components/ui";

// Retired 2026-08-30: this page used to duplicate the real PDF Studio's
// tools (merge/split/compress/etc.) against Shakthi OS's own DB -- a
// second, disconnected implementation of the same product name, not an
// admin view of the real one. The real, live product is
// dhansetu-pdf-studio, deployed via chatgpt.com/sites at the URL below.
// Founder's own instruction: this dashboard should link out to it, not
// re-implement it.
const LIVE_URL = "https://dhansetu-pdf-studio.sohamenterprice26.chatgpt.site";

export default function PdfStudioPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Dhansetu PDF Studio</h1>
      <Card>
        <CardHeader title="This is the real, live product" subtitle="Not a preview" />
        <CardBody>
          <p className="text-sm text-[var(--muted-foreground)] max-w-[60ch] mb-3">
            PDF Studio runs as its own real product, not inside this internal ops dashboard.
            Open it directly:
          </p>
          <a href={LIVE_URL} target="_blank" rel="noreferrer" className="text-sm font-medium underline">
            {LIVE_URL} →
          </a>
        </CardBody>
      </Card>
      <ComingSoon
        title="Real internal admin view (usage stats, paywall status, etc.)"
        note="An internal read-only view into the real product's own usage/paywall data would need a connection to that product's own D1 database (a different platform, chatgpt.com/sites) -- not built yet, distinct from the retired duplicate this page used to be."
      />
    </div>
  );
}
