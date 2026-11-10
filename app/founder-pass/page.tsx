import { redirect } from "next/navigation";

export default function FounderPassPage() {
  redirect("/checkout?tier=founder_pass");
}
