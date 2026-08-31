import { Card, CardHeader, CardBody, ComingSoon } from "@/components/ui";

// Retired 2026-08-30: this page used to duplicate the real PeopleDesk's
// staff/attendance/payroll management against Shakthi OS's own DB (its own
// peopledesk_staff/peopledesk_attendance tables) -- a second, disconnected
// implementation of the same product name, not an admin view of the real
// one. The real, live product is dhansetu-peopledesk, deployed via
// chatgpt.com/sites at the URL below. Founder's own instruction: this
// dashboard should link out to it, not re-implement it.
const LIVE_URL = "https://dhansetu-peopledesk.sohamenterprice26.chatgpt.site";

export default function PeopleDeskPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Dhansetu PeopleDesk</h1>
      <Card>
        <CardHeader title="This is the real, live product" subtitle="Not a preview" />
        <CardBody>
          <p className="text-sm text-[var(--muted-foreground)] max-w-[60ch] mb-3">
            PeopleDesk runs as its own real product, not inside this internal ops dashboard.
            Open it directly:
          </p>
          <a href={LIVE_URL} target="_blank" rel="noreferrer" className="text-sm font-medium underline">
            {LIVE_URL} →
          </a>
        </CardBody>
      </Card>
      <ComingSoon
        title="Real internal admin view (staff/attendance/payroll rollups)"
        note="An internal read-only view into the real product's own data would need a connection to that product's own D1 database (a different platform, chatgpt.com/sites) -- not built yet, distinct from the retired duplicate this page used to be."
      />
    </div>
  );
}
