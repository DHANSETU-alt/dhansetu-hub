import { redirect } from "next/navigation";

export default function SecurityScoreRoute() {
  redirect("/tools/seo-audit?mode=vendor-security");
}
