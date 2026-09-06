import { getDhansetuLinks } from "@/lib/api";
import { SUPPORT_EMAIL } from "@/lib/brand";

export const dynamic = "force-dynamic";

export default async function DhansetuLinkTreePage() {
  const { links } = await getDhansetuLinks();
  const active = links.filter((l) => l.active).sort((a, b) => a.sort_order - b.sort_order);

  return (
    <div className="fixed inset-0 overflow-y-auto" style={{ background: "#0a0c10", color: "#e8ecf1" }}>
      <div className="max-w-md mx-auto px-6 py-16 flex flex-col items-center text-center">
        <div
          className="w-20 h-20 rounded-full flex items-center justify-center text-2xl font-semibold mb-4"
          style={{ background: "radial-gradient(circle at 35% 30%, #dba95644, #0f131a 70%)", border: "1.5px solid #dba95688" }}
        >
          DA
        </div>
        <h1 className="text-2xl font-semibold">Dhansetu AI</h1>
        <p className="text-sm mt-1.5" style={{ color: "#a8b1c2" }}>Courses in Gujarati, built for real people, not filler.</p>

        <div className="w-full mt-8 space-y-3">
          {active.length === 0 ? (
            <div className="rounded-xl border p-5 text-sm" style={{ borderColor: "#2a3040", background: "#0f131a", color: "#a8b1c2" }}>
              No links added yet — honestly empty, not filled with placeholders. Real links go here once added.
            </div>
          ) : (
            active.map((l) => (
              <a
                key={l.id}
                href={l.url}
                target="_blank"
                rel="noreferrer"
                className="block w-full rounded-xl px-5 py-4 text-sm font-medium transition-colors"
                style={{ background: "#0f131a", border: "1px solid #2a3040", color: "#e8ecf1" }}
              >
                {l.title}
              </a>
            ))
          )}
        </div>

        <p className="text-xs mt-8" style={{ color: "#8b95a6" }}>
          Questions? <a href={`mailto:${SUPPORT_EMAIL}`} style={{ color: "#dba956" }}>{SUPPORT_EMAIL}</a>
        </p>
        <p className="text-[11px] mt-3" style={{ color: "#5b6472" }}>Powered by SHAKTHI OS</p>
      </div>
    </div>
  );
}
