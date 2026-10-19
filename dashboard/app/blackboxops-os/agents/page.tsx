import { loadSystemStatus, ACTIVITY_WINDOW_MINUTES } from "@/lib/systemStatus";
import MissionControlFlow from "@/components/MissionControlFlow";

export const dynamic = "force-dynamic";

// Same real backend as Mission Control, rebranded -- blackboxOps_OS's agent
// visualization is not a second implementation. "Single source of truth:
// GVC_OS Core. No duplicate development." -- this page proves that isn't
// just a slogan.
export default async function BlackboxAgentsPage() {
  const status = await loadSystemStatus();
  return (
    <MissionControlFlow
      status={status}
      activityWindowMinutes={ACTIVITY_WINDOW_MINUTES}
      brand={{ eyebrow: "blackboxOps_OS · Agent Visualization", title: "Live Agent Network", backLabel: "← blackboxOps_OS", backHref: "/blackboxops-os" }}
    />
  );
}
