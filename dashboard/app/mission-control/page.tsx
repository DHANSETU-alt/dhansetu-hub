import { loadSystemStatus, ACTIVITY_WINDOW_MINUTES } from "@/lib/systemStatus";
import MissionControlFlow from "@/components/MissionControlFlow";

export const dynamic = "force-dynamic";

export default async function MissionControlPage() {
  const status = await loadSystemStatus();
  return <MissionControlFlow status={status} activityWindowMinutes={ACTIVITY_WINDOW_MINUTES} />;
}
