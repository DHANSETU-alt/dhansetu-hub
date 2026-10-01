"use client";

import { useEffect, useRef, useState } from "react";
import { SHAKTHI_OS_VERSION } from "@/lib/version";

type Msg = { role: "user" | "bot"; text: string };

// Real chat widget wired to Shakthi_Agent (routing.run_task via
// --chat-message, still dispatched through the real pa_angella agent
// internally) -- not a scripted FAQ bot. Honestly reflects backend
// state: if the orchestrator API isn't reachable, it shows asleep rather
// than pretending to be available (founder's own explicit requirement).
export function BlackboxChatWidget() {
  const [open, setOpen] = useState(false);
  const [up, setUp] = useState<boolean | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    async function check() {
      try {
        const res = await fetch("/api/blackboxops/chat");
        const data = await res.json();
        if (!cancelled) setUp(!!data.up);
      } catch {
        if (!cancelled) setUp(false);
      }
    }
    check();
    const id = setInterval(check, 15000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  async function send() {
    const text = input.trim();
    if (!text || sending || !up) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setSending(true);
    try {
      const res = await fetch("/api/blackboxops/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      if (!res.ok) {
        setMessages((m) => [...m, { role: "bot", text: data.sleeping ? "I'm asleep right now -- the system's offline. Try again shortly, or email " + "support@dhansetuhub.in" : (data.error || "Something went wrong.") }]);
      } else {
        setMessages((m) => [...m, { role: "bot", text: data.reply }]);
      }
    } catch {
      setMessages((m) => [...m, { role: "bot", text: "Couldn't reach the system. Try again shortly." }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="fixed bottom-5 right-5 z-30" style={{ fontFamily: "'IBM Plex Sans', ui-sans-serif, sans-serif" }}>
      {open && (
        <div
          className="mb-3 w-[340px] max-h-[440px] rounded-2xl border flex flex-col overflow-hidden shadow-2xl"
          style={{ borderColor: "#1c2330", background: "#0f131a" }}
        >
          <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: "#1c2330" }}>
            <div className="flex items-center gap-2">
              <span
                className="w-2 h-2 rounded-full"
                style={{ background: up ? "#4ade80" : "#5b6472", boxShadow: up ? "0 0 6px #4ade80" : "none" }}
              />
              <span className="text-sm font-medium" style={{ color: "#e8ecf1" }}>
                {up === null ? "Checking…" : up ? `${SHAKTHI_OS_VERSION.osName} V${SHAKTHI_OS_VERSION.version} · Shakthi_Agent` : "Asleep — system offline"}
              </span>
            </div>
            <button onClick={() => setOpen(false)} className="text-xs" style={{ color: "#8b95a6" }}>close</button>
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2.5 min-h-[160px]">
            {messages.length === 0 && (
              <p className="text-xs" style={{ color: "#5b6472" }}>
                {up
                  ? "Ask Shakthi_Agent for a live dashboard review. It will rank unfinished work, plan the next steps, and call out authentication or manual actions that require you."
                  : "The system's asleep right now, so I can't answer live. Email support@dhansetuhub.in instead."}
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`text-sm leading-relaxed ${m.role === "user" ? "text-right" : ""}`}>
                <span
                  className="inline-block rounded-xl px-3 py-2 max-w-[85%]"
                  style={{
                    background: m.role === "user" ? "#dba95622" : "#0a0c10",
                    color: "#e8ecf1",
                    border: m.role === "bot" ? "1px solid #1c2330" : "none",
                  }}
                >
                  {m.text}
                </span>
              </div>
            ))}
            {sending && <p className="text-xs" style={{ color: "#5b6472" }}>thinking…</p>}
            <div ref={bottomRef} />
          </div>

          <div className="p-3 border-t flex gap-2" style={{ borderColor: "#1c2330" }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              disabled={!up}
              placeholder={up ? "Ask a question…" : "Offline right now"}
              className="flex-1 rounded-lg border px-3 py-2 text-sm disabled:opacity-50"
              style={{ borderColor: "#2a3040", background: "#0a0c10", color: "#e8ecf1" }}
            />
            <button
              onClick={send}
              disabled={!up || sending || !input.trim()}
              className="rounded-lg px-3 py-2 text-sm font-medium disabled:opacity-40"
              style={{ background: "#dba956", color: "#0a0c10" }}
            >
              Send
            </button>
          </div>
        </div>
      )}

      <button
        onClick={() => setOpen((o) => !o)}
        className="w-14 h-14 rounded-full flex items-center justify-center shadow-2xl relative"
        style={{ background: "#0f131a", border: `1.5px solid ${up ? "#4ade8088" : "#2a3040"}` }}
        aria-label="Open chat"
      >
        <span
          className="absolute w-2.5 h-2.5 rounded-full top-2 right-2"
          style={{ background: up ? "#4ade80" : "#5b6472", boxShadow: up ? "0 0 6px #4ade80" : "none" }}
        />
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M4 5.5C4 4.67 4.67 4 5.5 4h13c.83 0 1.5.67 1.5 1.5v9c0 .83-.67 1.5-1.5 1.5H9l-4 3.5v-3.5H5.5A1.5 1.5 0 0 1 4 14.5v-9Z"
            stroke={up ? "#4ade80" : "#8b95a6"} strokeWidth="1.5" strokeLinejoin="round"
          />
        </svg>
      </button>
    </div>
  );
}
