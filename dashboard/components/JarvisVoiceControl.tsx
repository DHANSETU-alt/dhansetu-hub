"use client";

import { useEffect, useRef, useState } from "react";

type SpeechResult = { results: ArrayLike<ArrayLike<{ transcript: string }>> };
type Recognition = {
  lang: string; interimResults: boolean; continuous: boolean;
  start: () => void; stop: () => void;
  onresult: ((event: SpeechResult) => void) | null;
  onerror: (() => void) | null; onend: (() => void) | null;
};
type RecognitionConstructor = new () => Recognition;
const LANGS = {
  en: { recognition: "en-IN", speech: "en-IN", label: "English" },
  hi: { recognition: "hi-IN", speech: "hi-IN", label: "हिन्दी" },
  gu: { recognition: "gu-IN", speech: "gu-IN", label: "ગુજરાતી" },
} as const;
type Language = keyof typeof LANGS;
type Phase = "IDLE" | "LISTENING" | "INTERPRETING" | "SPEAKING" | "ERROR";

const PHASE_UI: Record<Phase, { title: string; detail: string; color: string }> = {
  IDLE: { title: "READY", detail: "Tap Talk to Jarvis and speak", color: "text-[var(--local)]" },
  LISTENING: { title: "HEARING YOU", detail: "Speak now — your words will appear below", color: "text-cyan-300" },
  INTERPRETING: { title: "UNDERSTANDING", detail: "Prompt Master is structuring your request", color: "text-amber-300" },
  SPEAKING: { title: "RESPONDING", detail: "Jarvis is speaking the OS response", color: "text-emerald-300" },
  ERROR: { title: "CONNECTION ISSUE", detail: "Read the message below or use typed input", color: "text-[var(--bad)]" },
};

const FLOW: Array<{ phase: Phase; label: string }> = [
  { phase: "LISTENING", label: "HEARING" },
  { phase: "INTERPRETING", label: "UNDERSTANDING" },
  { phase: "SPEAKING", label: "RESPONDING" },
  { phase: "IDLE", label: "READY" },
];

export function JarvisVoiceControl() {
  const [language, setLanguage] = useState<Language>("en");
  const [phase, setPhase] = useState<Phase>("IDLE");
  const [transcript, setTranscript] = useState("");
  const [reply, setReply] = useState("");
  const [error, setError] = useState("");
  const [demoPhase, setDemoPhase] = useState<Phase | null>(null);
  const recognitionRef = useRef<Recognition | null>(null);
  const demoTimersRef = useRef<number[]>([]);
  const displayPhase = demoPhase ?? phase;

  function stopDemo() {
    demoTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    demoTimersRef.current = [];
    setDemoPhase(null);
  }

  useEffect(() => () => demoTimersRef.current.forEach((timer) => window.clearTimeout(timer)), []);

  function previewAnimation() {
    stopDemo();
    setTranscript("Show my priority tasks for today");
    setReply("");
    setError("");
    setDemoPhase("LISTENING");
    demoTimersRef.current = [
      window.setTimeout(() => setDemoPhase("INTERPRETING"), 1500),
      window.setTimeout(() => { setReply("Demo response: I found your priority tasks and prepared the mission summary."); setDemoPhase("SPEAKING"); }, 3000),
      window.setTimeout(() => setDemoPhase("IDLE"), 4800),
      window.setTimeout(() => setDemoPhase(null), 6000),
    ];
  }

  async function execute(text: string) {
    const clean = text.trim();
    if (!clean) return;
    stopDemo();
    setPhase("INTERPRETING"); setError("");
    try {
      const qs = new URLSearchParams({ text: clean, language });
      const response = await fetch(`/api/voice/execute?${qs.toString()}`, { cache: "no-store" });
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || "Command failed");
      const result = String(data.result || "No response returned.");
      setReply(result);
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(result);
        utterance.lang = LANGS[language].speech;
        utterance.onstart = () => setPhase("SPEAKING");
        utterance.onend = () => setPhase("IDLE");
        utterance.onerror = () => setPhase("IDLE");
        window.speechSynthesis.speak(utterance);
      } else setPhase("IDLE");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Voice command failed"); setPhase("ERROR");
    }
  }

  function listen() {
    stopDemo();
    const browser = window as typeof window & { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor };
    const Constructor = browser.SpeechRecognition || browser.webkitSpeechRecognition;
    if (!Constructor) { setError("Speech recognition is unavailable. Type the command below instead."); setPhase("ERROR"); return; }
    window.speechSynthesis?.cancel();
    const recognition = new Constructor(); recognitionRef.current = recognition;
    recognition.lang = LANGS[language].recognition; recognition.interimResults = false; recognition.continuous = false;
    recognition.onresult = (event) => { const text = event.results[0][0].transcript; setTranscript(text); void execute(text); };
    recognition.onerror = () => { setError("Microphone recognition failed or permission was denied."); setPhase("ERROR"); };
    recognition.onend = () => { recognitionRef.current = null; setPhase((current) => current === "LISTENING" ? "IDLE" : current); };
    setError(""); setReply(""); setPhase("LISTENING"); recognition.start();
  }

  function stop() { stopDemo(); recognitionRef.current?.stop(); window.speechSynthesis?.cancel(); setPhase("IDLE"); }

  return (
    <div className="rounded-xl border border-[var(--local)]/30 bg-[var(--surface)]/85 p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div><h2 className="text-base font-semibold">Talk to Jarvis</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Prompt Master → Guest permission gate → SHAKTHI action → spoken response</p></div>
        <div className="flex flex-wrap gap-2">{(Object.keys(LANGS) as Language[]).map((code) => <button key={code} onClick={() => setLanguage(code)} className={`rounded-full border px-3 py-1 text-xs ${language === code ? "border-[var(--local)] text-[var(--local)]" : "border-[var(--border)] text-[var(--muted-foreground)]"}`}>{LANGS[code].label}</button>)}</div>
      </div>
      <div className="relative mt-6 overflow-hidden rounded-2xl border border-[var(--local)]/25 bg-black/50 px-4 py-7 text-center">
        {demoPhase && <div className="absolute left-3 top-3 rounded-full border border-amber-400/60 bg-amber-400/10 px-2.5 py-1 font-mono text-[10px] font-bold tracking-wider text-amber-300">SIMULATED UI DEMO</div>}
        <div className="relative mx-auto flex h-32 w-32 items-center justify-center" aria-live="polite" aria-label={`${PHASE_UI[displayPhase].title}: ${PHASE_UI[displayPhase].detail}`}>
          {(displayPhase === "LISTENING" || displayPhase === "SPEAKING") && <><span className="absolute inset-0 rounded-full border border-cyan-300/30 animate-ping" /><span className="absolute inset-4 rounded-full border border-cyan-300/25 animate-ping [animation-delay:350ms]" /></>}
          {displayPhase === "INTERPRETING" && <span className="absolute inset-1 rounded-full border-2 border-transparent border-r-amber-300 border-t-amber-300 animate-spin" />}
          <div className={`relative flex h-24 w-24 items-center justify-center rounded-full border shadow-[0_0_45px_rgba(34,211,238,0.2)] ${displayPhase === "ERROR" ? "border-red-400/60 bg-red-500/10" : "border-cyan-300/50 bg-cyan-400/10"}`}>
            {(displayPhase === "LISTENING" || displayPhase === "SPEAKING") ? (
              <div className="flex h-10 items-center gap-1">{[4, 8, 14, 22, 14, 8, 4].map((height, index) => <span key={index} className="w-1 rounded-full bg-cyan-200 animate-pulse" style={{ height, animationDelay: `${index * 90}ms` }} />)}</div>
            ) : displayPhase === "INTERPRETING" ? <span className="text-2xl text-amber-200 animate-pulse">✦</span> : <span className="h-3 w-3 rounded-full bg-cyan-200 shadow-[0_0_16px_#67e8f9] animate-pulse" />}
          </div>
        </div>
        <div className={`mt-2 font-mono text-sm font-bold tracking-[0.2em] ${PHASE_UI[displayPhase].color}`}>{PHASE_UI[displayPhase].title}</div>
        <p className="mt-1 text-xs text-[var(--muted-foreground)]">{PHASE_UI[displayPhase].detail}</p>
        <div className="mx-auto mt-6 grid max-w-2xl grid-cols-4 gap-2">
          {FLOW.map((item) => <div key={item.label} className={`rounded-md border px-1 py-2 font-mono text-[9px] sm:text-[10px] ${displayPhase === item.phase ? "border-cyan-300/60 bg-cyan-300/10 text-cyan-200" : "border-white/10 text-[var(--muted-foreground)]"}`}>{item.label}</div>)}
        </div>
      </div>
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button onClick={phase === "LISTENING" || phase === "SPEAKING" ? stop : listen} disabled={phase === "INTERPRETING"} className="rounded-full border border-[var(--local)] bg-[var(--local-soft)] px-5 py-2 text-sm font-semibold text-[var(--local)] disabled:opacity-50">{phase === "LISTENING" ? "Stop listening" : phase === "INTERPRETING" ? "Interpreting…" : phase === "SPEAKING" ? "Stop speaking" : "Talk to Jarvis"}</button>
        <button type="button" onClick={previewAnimation} className="rounded-full border border-amber-400/30 px-4 py-2 text-xs text-amber-300">Preview animation</button>
        <span className="font-mono text-xs text-[var(--muted-foreground)]">REAL STATE: {phase}</span>
      </div>
      <form className="mt-4 flex flex-col gap-2 sm:flex-row" onSubmit={(event) => { event.preventDefault(); void execute(transcript); }}>
        <input value={transcript} onChange={(event) => setTranscript(event.target.value)} placeholder="Or type: Shakthi, show system status" className="min-w-0 flex-1 rounded-md border border-[var(--border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--local)]" />
        <button className="rounded-md border border-[var(--border)] px-4 py-2 text-sm" type="submit">Send</button>
      </form>
      {reply && <p className="mt-4 rounded-md bg-[var(--surface-2)] p-3 text-sm">Jarvis: {reply}</p>}
      {error && <p className="mt-4 text-sm text-[var(--bad)]">{error}</p>}
      {demoPhase && <p className="mt-3 rounded-md border border-amber-400/20 bg-amber-400/5 p-2 text-[11px] text-amber-200">UI DEMO ONLY — no microphone input, OS action, or agent activity is occurring.</p>}
      <p className="mt-3 text-[11px] text-[var(--muted-foreground)]">Browser microphone permission is requested on first use. Owner-restricted commands remain unavailable until secure owner authentication is configured.</p>
    </div>
  );
}
