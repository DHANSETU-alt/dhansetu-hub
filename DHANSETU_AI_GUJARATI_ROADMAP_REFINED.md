# dhansetu_ai — Gujarati AI Product Suite: Refined Roadmap

Source: `~/Downloads/Dhansetu-AI-Gujarati-Agent-Roadmap.xlsx` (imported 2026-09-08).
Tracked as **Task 17 (#27)** in Shakthi_OS.

## How this decision was made — read before acting on it

This was supposed to go through Shakthi_OS's own CEO agent (`orchestrator/ceo.py`),
escalated to Claude. That didn't happen as designed, for two real, verified reasons:

1. **Cloud escalation is unavailable**: `ANTHROPIC_API_KEY` is not set in this
   environment, so `model_gateway.call_cloud()` cannot reach Claude at all.
2. **Local fallback timed out**: the goal was classified `risk="normal"` (it
   didn't hit `routing.py`'s exact `CRITICAL_KEYWORDS`/`HIGH_KEYWORDS` phrases),
   so it ran on the local model (`gemma4`, 9.6GB). Ollama's server was confirmed
   running, but the call exceeded the configured 420s timeout on this prompt
   size and failed with `TimeoutError`.

Rather than fake a system-generated verdict, the evaluation below was done
**directly by Claude (this session)**, using the exact same rubric
`agents/ceo.yaml` defines (priority/risk/business_impact, 1-10, plus a
status of approved/rejected/revise). This is a real gap worth fixing —
see the note at the bottom.

## CEO-style verdict

```
status: revise
priority_score: 5
risk_score: 7
business_impact_score: 6
```

**Reason:** Worth pursuing — real underserved niche (Gujarati-first AI
tools), near-zero infra cost, a genuine 3-tier funnel — but risky as
written on money and content-integrity grounds, and not the most urgent
thing on the board right now (the blackboxops.co.in domain cutover and
Razorpay go-live are still open and more time-sensitive).

### Why risk is scored high (7/10) — specific, not generic

1. **Mocked AI output behind a paid funnel.** The spreadsheet's own Day-1
   prompt says "mock Claude response" and "mock images." ArthSetu's product
   is mutual-fund/tax analysis — shipping a *fake* AI response dressed as
   real financial analysis, even briefly, is a real trust and potential
   consumer-protection problem, not a cosmetic shortcut. Fine for an
   internal demo; not fine once email capture and pricing pages go live
   pointing at it.
2. **GitHub Models API for a commercial product.** The plan routes all
   three products through `https://models.github.ai/inference` (GitHub's
   free-tier model access). That tier's terms are built around evaluation/
   personal use, not backing a paid SaaS with Pro/Enterprise tiers charging
   real money. Worth confirming GitHub's actual terms before building the
   whole pipeline on it — or route through Shakthi_OS's own
   `model_gateway.py` instead (it already does real local-first + optional
   Anthropic cloud, with cost tracking built in).
3. **No disclaimer path for financial content.** ArthSetu gives tax/
   investment commentary in Gujarati to a non-English-fluent audience —
   add a visible "AI-generated, not certified financial advice" line before
   any Pro conversion, not after.

### What "revise" means concretely — do these before Day 1 build

- Replace every "mock" step with either a real (even if narrow) model call,
  or a clearly-labeled "Preview / Beta" watermark on anything shown to a
  real user before the AI call is real.
- Confirm GitHub Models' terms allow this commercial use, or swap the
  pipeline to Shakthi_OS's existing `model_gateway.call_local/call_cloud`
  before building GyaanSetu/VyaparSetu clones on the same base.
- Add a financial-content disclaimer to ArthSetu before Pro launch.
- Consider compressing Day 1-2 into a pure landing-page + email-capture
  validation step (no build) before committing to all three products —
  the plan already does this in spirit for the free-tool funnel, but
  builds the full ArthSetu tool on Day 1 itself with no signal check first.

Everything else in the original plan — the 3-product structure, the
Fortune500 free→Pro→Enterprise funnel, the no-GPT/Claude-branding rule,
the 30-day sequencing — is sound and unchanged.

---

## Original roadmap (as imported, unedited)

### Brand rules

| | |
|---|---|
| BRAND | dhansetu_ai - AI શીખો _ એઆઈ જ્ઞાન (Gujarati Only) |
| OWNER | Gaurav Chauhan - Sanand, Gujarat - IG @dhansetu_ai |
| RULE 1 | All products in Gujarati language. UI in Gujarati + English mix. No FinanceGPT name. |
| RULE 2 | Use Claude (Anthropic) via GitHub Models, NOT OpenAI. Names: DhanSetu AI, ArthSetu, GyaanSetu etc — no GPT word. |
| RULE 3 | Fortune500 strategy: Free Tool → Email Capture → Pro Subscription → Enterprise (schools/businesses). |
| GOAL | Build 3 Gujarati AI products under dhansetu_ai that earn recurring income from Gujarat audience. |
| TOMORROW START | Build first free tool, launch on dhansetu_ai IG reel. |

### The 3 products

**P1 — ArthSetu AI (ધનનું જ્ઞાન)** — "તમારા પૈસાનું AI વિશ્લેષણ"
Free: upload mutual fund statement, AI explains profit/loss in Gujarati.
Pro ₹2499/mo: unlimited portfolio scans + tax-saving advice + WhatsApp alerts.
Enterprise ₹82k/mo: for CAs/financial advisors, manage 100 clients, private AI.
Target: Gujarat CAs, Ahmedabad/Sanand traders, 30-50yo.

**P2 — GyaanSetu AI Lab (અભ્યાસ)** — "AI શીખો - ગુજરાતીમાં"
Free: Gujarati-text prompt → AI poster/image generator.
Pro ₹1599/mo: 100+ Gujarati AI video courses, certificate, private chatbot.
Enterprise ₹41k/mo: white-label AI Lab for schools/coaching.
Target: Gujarati students, shopkeepers, homemakers without English.

**P3 — VyaparSetu AI (ધંધાનો સાથી)** — "તમારા ધંધા માટે AI"
Free: 100 viral Gujarati captions + hashtags + poster ideas for shops.
Pro ₹3299/mo: Instagram DM auto-reply in Gujarati, leads to Google Sheet, 1000 DM/mo.
Enterprise ₹1.2L setup + ₹16k/mo: full shop AI bot, Gujarati voice replies.
Target: Sanand/Ahmedabad shopkeepers, Instagram sellers, boutiques/bakeries.

### 30-day build plan

| Day | Focus | Output |
|---|---|---|
| D1 AM | Setup Claude via GitHub Models, repo `dhansetu-arthsetu` | Repo + test.py working |
| D1 PM | Build ArthSetu free tool (Jarvis-style UI, PDF upload, email capture, mock AI result) | Live on GitHub Pages |
| D2 | Google Sheets email logging, social-proof dashboard, feedback form | 100 Gujarati emails collected |
| D3-7 | Pro plan page, Razorpay checkout | Pro page live |
| D8-15 | Clone for GyaanSetu + VyaparSetu | All 3 tools live |
| D16-30 | Hub site, Enterprise page, Calendly, cross-sell | Hub live + 5 enterprise calls |

Exact Claude Code prompts for each build step are preserved in the source
spreadsheet (`00_FOR_CLAUDE_AGENT`, `02_30Day_Roadmap_Gujarati`,
`03_Claude_Prompts_Gujarati` sheets) — not duplicated here since they're
copy-paste-ready as-is; pull them directly from the xlsx when starting a
build day.

---

## Real system gap this surfaced

Shakthi_OS's CEO decision pipeline currently cannot reach either model tier
reliably for a prompt this size: no cloud key configured, and the local
model's default 420s timeout is too tight for gemma4 on a long/complex
goal. Worth a v6 fix (see `docs/V6_PROGRESS.md`): either raise
`SHAKTHI_OLLAMA_TIMEOUT` for CEO-tier decisions specifically, or split long
goals into a summarize-then-decide two-step call the way `pa_angella.py`
already does for its own long-input problem.
