import { redirect } from "next/navigation";
import { WelcomeStatus } from "@/components/payment/WelcomeStatus";
export default function WelcomePage({ searchParams }: { searchParams: { order?: string } }) {
  if (!searchParams.order) redirect("/");
  return <main className="min-h-screen bg-slate-50 px-4 py-20"><WelcomeStatus orderId={searchParams.order} /></main>;
}
