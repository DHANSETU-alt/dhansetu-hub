# Hermes Agent (Nous Research) — Competitive Research + Shakthi_OS Advancement Plan

**Source:** live fetch of https://hermes-agent.nousresearch.com/, 2026-09-08. Everything under "What Hermes Agent actually offers" below is from that page directly — not assumed. Everything under "Shakthi_OS today" is from this session's own direct code audit (Days 1-5 of `V6_PROGRESS.md`), not assumed either.

## What Hermes Agent actually offers (real, per their own site)

- **Multi-platform, one memory**: Telegram, Discord, Slack, WhatsApp, Signal, Email, CLI — same agent, same memory, across all of them.
- **Persistent memory that auto-generates skills** — it doesn't just store facts, it retains *how it solved problems* for reuse.
- **Natural-language automation**: schedules its own reports/backups/briefings from a plain-English request, no cron-syntax involved.
- **Task delegation to isolated subagents** — spawns subagents with independent conversations and Python RPC scripts, each running in a real sandboxed backend (local, Docker, SSH, Singularity, or Modal), with container hardening and namespace isolation.
- **Multimodal tool access**: web search, browser automation, vision, image generation, text-to-speech.
- **Multi-model, not single-model**: 300+ models through "Nous Portal" — the opposite of a single-AI-provider bet.
- **Native desktop apps**: macOS 12+, Windows 10/11, Linux — not just a web dashboard.
- **Open source (MIT)**, tiered subscription (Free/Plus/Super/Ultra) for credits + model access.

## Shakthi_OS today, honestly (from this session's own audit, not aspirational)

**Real and working:** 27-agent YAML-driven registry (add an agent = write a file, no core changes), real risk-classified task routing with a full audit trail (`cost_ledger`, `task_events`), a real voice pipeline (STT/wake-word/TTS — built but not wired into a continuous loop), deep *business-specific* domain modules (finance, sales, marketing, security, sentinel, real payment gateway integrations) that Hermes has no equivalent of at all, 462 passing tests, a genuinely impressive live dashboard visualization.

**Real gaps vs. Hermes, honestly:**
1. **No multi-platform conversational surface.** Shakthi_OS has Telegram *alert* delivery (one-way, cron-triggered) — not a two-way conversational Angella you can message from your phone. Real, closeable gap: the Telegram plumbing already exists (`orchestrator/telegram_service.py`), it's just never been wired for inbound conversation.
2. **No skill-learning memory.** `memory_entries` has a `layer` column that already includes `'lesson'` in its own schema comment — but nothing actually *writes* a structured, reusable "here's how I solved X" record yet. The column exists; the behavior doesn't.
3. **No sandboxed subagent execution.** Every Shakthi_OS agent call runs in-process, no isolation. Hermes's Docker/SSH/Modal backend model is a real security/reliability edge — bigger, riskier architecture change, not a quick win.
4. **No general browser-automation/vision/image-gen toolkit any agent can reach.** Shakthi_OS has one narrow `chrome_developer` agent role; Hermes offers this as a first-class capability across the whole system.
5. **300+ models vs. effectively 2-3 local models + optional single cloud escalation.** This is the one gap *not* worth closing — see below.

## The strategic answer to "more advanced, with Claude as the single AI tool"

Don't chase Hermes's 300-model breadth — that's their bet, not a gap to close. A single-model bet on Claude specifically is a **real, coherent, defensible position**, not a limitation, for three concrete reasons:
1. **Claude's actual frontier strength is agentic tool use and computer use**, not raw model-menu breadth. Leaning into that hard — real desktop/browser control, not just scoped internal function calls — plays to Claude's real edge rather than competing on a metric (model count) Shakthi_OS can't win.
2. **Depth beats breadth for this founder's actual business.** Hermes is a general-purpose personal agent; Shakthi_OS already has something Hermes structurally can't — real, working payment gateway code, real Indian-market context (PayU/Razorpay/GST-adjacent business logic), real Gujarati/Hindi/English handling, real per-business operating modules. "One frontier model, deeply wired into your actual revenue systems" is a stronger pitch than "300 models, none of them know your business."
3. **Cost discipline**: local-first with one deliberate cloud escalation path (already built, `routing.py`'s risk-based escalation) is real, working cost control that a 300-model marketplace doesn't optimize for.

### Concrete next-task recommendations, ranked by real leverage vs. effort

1. **Wire Angella into Telegram as a real two-way conversation**, not just outbound alerts. Plumbing exists; this closes the single biggest visible gap (multi-platform presence) cheapest.
2. **Give Angella real computer-use capability** (the same category of tool this session uses via `claude-in-chrome`) so she can actually operate the founder's browser/apps on request — the genuine Claude-specific edge Hermes's "browser automation" claim is trying to approximate generically.
3. **Make the `lesson` memory layer real** — after a task completes, write a structured "what worked / what didn't" record an agent can retrieve next time it faces something similar. The schema already has the column; this is implementation, not design.
4. **Only after those**: sandboxed subagent execution (Docker/similar) — real, but a genuine architecture project, not a quick win, and Shakthi_OS's current in-process model hasn't caused an actual incident yet, so it's prioritized honestly below the cheaper, higher-visibility wins above.

**Not recommended:** chasing multi-model breadth to match Hermes's 300+ models. That directly contradicts the founder's own framing of this question ("single AI tool Claude") and isn't where Shakthi_OS's real advantage lives.
