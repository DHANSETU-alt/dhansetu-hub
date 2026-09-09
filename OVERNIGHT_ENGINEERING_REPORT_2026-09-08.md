# SHAKTHI_OS — Overnight Engineering Report
**Session start:** 2026-09-08 21:59 IST — **Status:** IN PROGRESS (updated live as work completes)

Every line below is something actually executed and observed this session — nothing here is projected or assumed. Operational note up front: this is one continuously active Claude Code session, not a detached background process; "overnight" below means real work completed while this session stayed active, not unattended multi-hour autonomy.

---

## COMPLETED TASKS (evidence-backed)

*(populated as work finishes below)*

## BLOCKED TASKS

*(populated as blockers are found)*

## COMPLETED — Website status audit (real DNS + HTTP checks, not assumed)

1. **Correcting myself within this same report:** I initially misread blackboxops.co.in's status as new progress. Re-checked against memory before publishing this claim — it's not. The domain resolves fine (real Cloudflare IPs) and returns HTTP 200, but the page title is still **"BlackBoxOps AI — AI-assisted operations for small agencies"** — the *old* agency-consulting page. That's the exact same stuck state a prior session already root-caused and documented in detail (`project_blackboxops_co_in_relaunch` memory): the real BlackboxOps_OS relaunch build exists and works, but something between DNS and the Cloudflare Worker/ChatGPT-Sites layer is still intercepting the real domain before the new build can serve. That prior session tried two real fixes (Custom Domain route, Workers Route) and hit a genuine OAuth-scope wall reading DNS records — concluded it needs the founder to open the Cloudflare dashboard directly and share what's actually in the DNS tab. **Still true tonight, unchanged. Not re-attempting the same diagnosed dead end.**

2. **dhansetuhub.in is live and reachable** — HTTP 200, served via Cloudflare.

3. **dhansetuhub.info is COMPLETELY UNREACHABLE for everyone, not just this machine** — real, critical bug. `dig +short dhansetuhub.info @8.8.8.8` (public DNS, no local cache involved) returns `127.0.0.1`. That's the site's actual public DNS A record pointing at loopback — anyone visiting this domain worldwide gets sent to their own machine, not the real Cloudflare Worker. Confirmed not a local `/etc/hosts` override (checked, none exists) — this is a real DNS misconfiguration at the registrar/DNS provider level. **FOUNDER ACTION REQUIRED**: fix the A/CNAME record for dhansetuhub.info to point at the real Cloudflare Worker, not 127.0.0.1. I cannot fix this myself — it requires DNS provider access I don't have.

## COMPLETED — Priority 2: Razorpay webhook receiver (real gap, now closed)

`orchestrator/payments.py`'s own module docstring flagged this as missing: "No webhook receiver -- this system is localhost-only by design... payment status is checked on demand." Built the real thing:

- `payment_gateway_manager.verify_razorpay_webhook_signature()` — HMAC-SHA256 over the raw request body, Razorpay's documented formula.
- `orchestrator/cli.py --process-razorpay-webhook` — verifies, parses the event, updates `payment_transactions` status (`payment.captured`/`order.paid` → paid, `payment.failed` → failed). Idempotent (webhooks retry), fails loud on bad signature (never silently accepts), reports (not silently drops) events for orders this system doesn't recognize.
- `dashboard/app/api/blackboxops/razorpay-webhook/route.ts` — the real HTTP endpoint. Uses `req.text()`, not `req.json()`, specifically because the signature covers exact raw bytes — a real, documented gotcha, tested for.
- **4 new signature tests** (valid, tampered body, wrong secret, garbage signature) — 462/462 full suite passes.
- **Live end-to-end proof, not just unit tests**: inserted a real `payment_transactions` row, sent a correctly-signed webhook through the actual CLI path, confirmed the DB row genuinely flipped to `paid`. Then sent a bad-signature webhook against the same row, confirmed it was rejected with zero side effects (status unchanged). Test data cleaned up afterward — DB left exactly as found.
- The HTTP route itself correctly fails closed (500) when `RAZORPAY_WEBHOOK_SECRET` isn't configured, rather than silently accepting unverified webhooks — same credential gap as everything else payment-related tonight, not a code gap.

**FOUNDER ACTION REQUIRED (when ready):** once real Razorpay keys exist, set `RAZORPAY_WEBHOOK_SECRET` (from Razorpay dashboard → Webhooks, a value distinct from the API Key Secret) and register `https://<your-domain>/api/blackboxops/razorpay-webhook` as the webhook URL there.

## COMPLETED — Backups (safe, local, reversible)

Full V6 (`shakthi-os`) and blackboxops-cleaner backups created locally (repo tarballs + DB snapshot). **NOT copied to SHAKTHI_SSD and the SSD was NOT formatted** — irreversible action, founder asleep/unreachable until 4:30 AM, explicitly held for his own sign-off per this session's safety rules (holds even under his "don't ask me, use your judgment" instruction — that instruction doesn't extend to irreversible actions, told him this directly and he accepted it before going to sleep). Backups are ready to copy the moment he confirms.

## COMPLETED — Hermes Agent (Nous Research) competitive research

Founder-requested: audit hermes-agent.nousresearch.com, research how Shakthi_OS could exceed it while staying single-model (Claude), for a future task. Full writeup: `docs/HERMES_AGENT_COMPETITIVE_RESEARCH_2026-09-08.md`, tracked as **OS 5 (Project 4 in DB terms — actually registered correctly as OS-track, see bug fix below)**. Short version: Hermes wins on multi-platform presence (Telegram/Discord/Slack/WhatsApp/Signal) and sandboxed subagent execution (Docker/SSH/Modal); Shakthi_OS's real, defensible edge is depth over breadth — real business-specific modules (payments, Indian market context, Gujarati/Hindi/English) a 300-model generalist can't match. Ranked recommendations: (1) wire Angella into Telegram for real two-way conversation — plumbing already exists, cheapest big win; (2) real computer-use capability for Angella; (3) make the already-half-built `lesson` memory layer actually write structured reusable records; (4) sandboxed subagent execution, correctly flagged as a real architecture project, not a quick win.

## COMPLETED — Real bug found and fixed: OS-track initiatives mislabeled "Project" everywhere

Found while registering the research above as an OS-track item — the CLI printed "Project 4" for something correctly stored as OS-track #4 in the database (verified via direct DB query: `track='os', seq=4` — display bug only, data was always correct). Traced to the ORIGINAL source of a bug pattern I'd already patched twice earlier tonight in two other functions (`_cmd_milestone_add`, `_cmd_initiative_status`) without realizing I'd missed the actual root cause in `_cmd_initiative_add` itself. Fixed properly now — all three call sites use the same correct track→label logic. Live-verified: created a real test OS-track item, confirmed it now prints "OS 5" correctly, then removed the test data. 462/462 tests still pass.

## Priority 1 (Auth) — honest note, not re-verified further

Attempted a fresh check tonight (curl against guessed route paths on dhansetuhub.in) — not meaningful evidence one way or the other, since I don't have access to the production log tooling ("Sites AI") the original diagnosis used, and guessed route names returning 404/307 doesn't confirm or deny the actual bug. **Not claiming re-verification I don't actually have.** What stands: the root cause was already definitively found earlier (`invalid_client`, wrong `GOOGLE_CLIENT_SECRET` on the Sites deployment) via real production log analysis + a real end-to-end test attempt — that finding is solid, still the accurate status, and still blocked on the founder retrieving the real secret from Google Cloud Console (already opened for him earlier tonight, exact OAuth client confirmed: "Dhansetu SmartBudget"). Nothing new to report here beyond confirming that diagnosis still stands as the real, current state.

## COMPLETED — Customer-facing Support Bot (real gap found: existing chat widget is founder-internal, not customer-facing)

Checked before building anything new — a chat widget already exists (`dashboard/app/api/blackboxops/chat/route.ts`), but it's the founder's own internal ops assistant (pulls his live task/initiative snapshot, answers as his delivery partner) — not a public FAQ/lead-capture bot for site visitors. That's a real, still-open gap against the brief's actual ask.

**Built:** `orchestrator/support_bot.py` (new module) on top of two things that already existed — `knowledge.ask()` (real plain-text search + synthesized answer, honest "no match" behavior) and `sales.ingest_lead()` (real scoring/escalation pipeline every other lead goes through). CLI (`--support-bot-ask`) + a public Next.js route (`/api/blackboxops/support`) — deliberately separate module and route from the internal chat widget, enforced in two places (backend module docstring + route comment), with a dedicated test (`test_never_leaks_internal_dashboard_data`) confirming the response shape never carries the founder's task/initiative data.

**Real bug found via live testing, not assumed:** `db.search_knowledge()`'s LIKE-based matching pulled loosely-related internal documents for an unrelated question (asked about Tally integration, got back the Sales Playbook / Mascot Brief / an ops report) — the model itself correctly refused to fabricate an answer ("cannot be found in the provided documents"), but my first version's `matched = bool(sources)` check would have shown that honest non-answer to a real customer as if it were a real one. Fixed: now also checks the answer text for the model's own refusal phrasing before calling it "matched." Re-verified live against the exact same real question — now correctly falls through to lead capture instead.

**Real, still-open gap, not silently hidden:** the knowledge base currently has zero customer-facing FAQ content — only internal docs (Wifi password, internal sales playbook, an ops report). The bot's plumbing is real and tested, but it has nothing useful to answer real customer questions with yet. Needs real FAQ content seeded (`knowledge.add_document()`) before this is actually useful on a live site — flagged as next-task, not fabricated as done.

**A mistake I made and fixed, logging honestly:** while cleaning up my own test data, an over-broad `DELETE FROM leads WHERE email LIKE '%example.com%'` also deleted two real pre-existing leads from 2026-08-24 (Priya Sharma, Rohan Mehta) that happened to use `.example.com` demo addresses. Caught it by checking `created_at` against tonight's backup before assuming they were mine, restored both rows from the backup taken earlier tonight, verified byte-for-byte identical to the original. No data lost, but a real reminder to check before broad deletes even on what looks like obviously-disposable test data.

5/5 new tests pass, 462+ full suite unaffected. Tracked as a milestone on **Task 13** (Founder Command Center) — closest existing initiative; consider a dedicated initiative if this becomes a bigger workstream.
