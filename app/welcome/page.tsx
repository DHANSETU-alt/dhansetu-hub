import { redirect } from "next/navigation";
import { WelcomeStatus } from "@/components/payment/WelcomeStatus";
export default async function WelcomePage({ searchParams }: { searchParams: Promise<{ order?: string }> }) {
  const params = await searchParams;
  if (!params.order) redirect("/");
  return <main className="min-h-screen bg-slate-50 px-4 py-20"><WelcomeStatus orderId={params.order} /></main>;
}
