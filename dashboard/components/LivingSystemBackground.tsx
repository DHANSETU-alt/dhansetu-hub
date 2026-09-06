"use client";

import { MatrixRain, FireflySwarm } from "@/components/AmbientEffects";

// The same "living system" ambient layers as Mission Control -- matrix
// rain, fireflies, radar sweep -- reused here as a decorative page
// background instead of Mission Control's full interactive org tree.
// Deliberate choice, not a shortcut: Mission Control's tree carries 23
// labeled agent nodes meant to be read up close on an internal ops
// screen. Behind real marketing copy on a customer-facing page, that much
// readable text would fight the actual sales message instead of
// supporting it -- so this keeps the ambient atmosphere (which is
// genuinely the "wow" part) and leaves the literal org chart on the
// internal dashboard where it belongs. Say the word if you want the full
// tree here instead; it's a one-line swap.
//
// Fixed, behind everything (-z-10), pointer-events none throughout so it
// never intercepts a click or scroll on the real page content in front of
// it. Drop <LivingSystemBackground /> as the first child of a page with a
// dark background and it just sits behind whatever renders after it.
export function LivingSystemBackground() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none" style={{ background: "radial-gradient(ellipse at 50% 30%, #0d1420 0%, #05070a 70%)" }}>
      <style>{`
        @keyframes livingBgRadarSpin { to { transform: rotate(360deg); } }
        @keyframes livingBgRipple {
          0%   { transform: scale(1);   opacity: 0.55; }
          100% { transform: scale(14);  opacity: 0; }
        }
      `}</style>

      <MatrixRain />
      <FireflySwarm count={140} />

      <div
        className="absolute rounded-full"
        style={{
          width: "70vmax", height: "70vmax", left: "50%", top: "40%", marginLeft: "-35vmax", marginTop: "-35vmax",
          background: "conic-gradient(from 0deg, transparent 0deg, rgba(167,139,250,0.35) 14deg, transparent 70deg)",
          animation: "livingBgRadarSpin 7s linear infinite",
          mixBlendMode: "screen",
        }}
      />
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="absolute rounded-full"
          style={{
            left: "50%", top: "40%", width: 20, height: 20, marginLeft: -10, marginTop: -10,
            border: "1px solid rgba(34,211,238,0.4)",
            animation: `livingBgRipple 4.2s ease-out ${i * 1.4}s infinite`,
          }}
        />
      ))}
    </div>
  );
}
