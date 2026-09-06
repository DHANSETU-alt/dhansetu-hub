import { getWebsiteHealthLatest, getWebsiteHealthIncidents } from "@/lib/api";
import { WebsiteHealthWatcher } from "@/components/WebsiteHealthWatcher";

export default async function WebsiteHealthPage() {
  const [{ sites }, { incidents }] = await Promise.all([
    getWebsiteHealthLatest(),
    getWebsiteHealthIncidents(50),
  ]);
  return <WebsiteHealthWatcher initialSites={sites} initialIncidents={incidents} />;
}
