import { redirect } from "next/navigation";

// The imported Google AI Studio experience is the canonical DhansetuHub root.
// Existing application routes and the Razorpay payment boundary remain intact.
export default function Home() {
  redirect("/aistudio/index.html");
}
