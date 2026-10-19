import JarvisMissionGraph from "@/components/JarvisMissionGraph";
import { loadSystemStatus } from "@/lib/systemStatus";

export const dynamic = "force-dynamic";

export default function JarvisPage() {
  return (
    <div className="relative min-h-[calc(100vh-10rem)] overflow-hidden rounded-[2rem] border border-cyan-300/10 bg-black/20 p-4 shadow-[0_0_80px_rgba(34,211,238,0.08)] sm:p-6">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(34,211,238,0.12),transparent_42%)]" />
      <div className="relative z-10"><JarvisMissionGraph status={loadSystemStatus()} /></div>
    </div>
  );
}
