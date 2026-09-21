import { PartnerApplicationForm } from "@/components/partners/PartnerApplicationForm";

export default function JoinAsExpertPage() {
  return <main className="mx-auto max-w-2xl space-y-6 p-5 sm:p-8"><h1 className="text-3xl font-bold text-slate-900">Join as an expert</h1><p className="text-slate-600">Applications are reviewed before any profile, referral link, or customer-facing service is enabled.</p><PartnerApplicationForm initialKind="tax_provider" /></main>;
}
