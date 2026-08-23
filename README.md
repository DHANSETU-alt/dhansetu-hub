# Shakthi OS (v4)

14 agents routed local-first through Ollama, a web dashboard, a Telegram
command/alert bot, Google Sheets as the official ledger, a Bug Fixer +
Audit workflow, real Mac system monitoring (Sentinel), a multilingual
family assistant (Buddy) with a real Safe Mode filter, a Knowledge base,
and voice control (Voice Commander) with Owner/Family/Guest permissions.

Personal-first: this runs on your Mac, for you. Same codebase as every
prior phase (Phase 0.1 → 0.4 → v4) — "v4" is a mission expansion, not a
rewrite.

## What's new in v4

- **SHAKTHI SENTINEL** (`orchestrator/sentinel.py`): real `psutil` readings
  — CPU/RAM/swap/disk/battery/internet/Ollama/DB — every field either a
  live number or an honest `null` (CPU temperature needs `sudo` via
  `powermetrics`, confirmed unavailable without it on this machine; Docker
  confirmed not installed). Deterministic Health/Performance scores (0-100).
  `--sentinel-check` to run once; wire into cron for continuous monitoring.
- **SHAKTHI KNOWLEDGE** (`orchestrator/knowledge.py`): a real knowledge
  base (`knowledge_documents`), plain-text multi-word search (a real bug
  was caught and fixed live here — the first version matched the *entire
  question* as one substring, which almost never hits; fixed to match on
  individual significant words).
- **SHAKTHI BUDDY** (`orchestrator/buddy.py`): Gujarati/Hindi/English
  mixed family assistant, Child/Family/General modes. Safe Mode is a real
  deterministic keyword filter checked on *both* the input and the model's
  output — not prompting alone, the same reasoning that put deterministic
  checks in `security.py` and the Bug Fixer's patch scanner. Live-verified:
  a Hindi story request produced a real appropriate story; "how to make a
  bomb" was blocked instantly, before any model call.
- **SHAKTHI VOICE COMMANDER** (`orchestrator/voice.py`): mic → raw PCM
  (`sounddevice`, no ffmpeg needed) → local transcription (`faster-whisper`
  "base") → fuzzy wake-word match → intent routing → Owner/Family/Guest
  permission check → real agent/report call. **Live-verified end to end**
  with a synthesized test utterance: transcribed "Shakthi check my finance
  report" as "Shout-T check my finance report" (an unusual proper noun,
  plausible mishear), correctly fuzzy-matched the wake word, correctly
  routed to finance, and **correctly denied a guest identity** while
  **correctly granting an owner identity** the same request — the
  permission boundary is enforced, not decorative.
- **Owner/Family/Guest** (`orchestrator/access.py`): passphrase-based,
  same manual-entry-only pattern as Telegram/Sheets credentials. Unknown
  or missing passphrase always resolves to `guest` — fails toward least
  privilege.
- Real, live-hit engineering friction from getting Voice Commander running
  on this exact machine, documented because it's genuinely useful if this
  breaks again: PyTorch (and therefore `openai-whisper`) has **no wheels
  for Python 3.14** — hard upstream blocker, not fixable here. Switched to
  `faster-whisper` (a C++ engine, not PyTorch) with `--no-deps` to skip its
  `av`/PyAV dependency (needs `pkg-config`, no Homebrew on this machine) —
  audio is captured directly as PCM via `sounddevice`, so the file-decoding
  `av` was never actually needed. See `requirements.txt` for the full story.

## v4 usage

```bash
# Sentinel
python3 -m orchestrator.cli --sentinel-check

# Knowledge
python3 -m orchestrator.cli --knowledge-add "Wifi password" --content "..." --tags "office"
python3 -m orchestrator.cli --knowledge-ask "where is the wifi password"

# Buddy
python3 -m orchestrator.cli --buddy-chat "tell me a story" --buddy-mode child --session-id family1

# Voice Commander (records from the real mic — macOS will prompt for
# microphone permission the first time; grant it in System Settings > Privacy)
export SHAKTHI_OWNER_PASSPHRASE="pick-something-only-you-know"
python3 -m orchestrator.cli --voice-listen --seconds 5 --owner-passphrase "pick-something-only-you-know"
```

## Known v4-specific gaps

- Hindi/Gujarati voice transcription is not live-verified — no Gujarati
  TTS voice exists on this machine to generate a test utterance, and a
  clean Hindi test would need actual Devanagari input, not a
  Hindi-influenced phrase spoken in an English voice (which is what was
  tried, and predictably transcribed poorly). Whisper's documented
  multilingual support covers both; it just isn't independently re-verified
  here the way English was.
- Voice Commander's intent router is a small fixed keyword list (finance,
  security, website, sentinel, bug scan, else falls back to Buddy) — not a
  general NLU system. Expanding it is additive (new tuples in
  `voice.INTENTS`... actually `detect_intent`'s if-chain), not a redesign.
- `--sentinel-check` runs once per invocation; continuous monitoring needs
  a cron entry (same pattern as `scheduled_reports.py`) — not set up by
  default.
- Owner/Family/Guest is passphrase-only, no voice-print/speaker
  recognition — anyone who knows the passphrase (spoken or typed) is that
  identity. Reasonable for a household, not a real biometric boundary.

---

# Phase 0.4 (still current)

- **Bug Fixer** (`orchestrator/bug_fixer.py`): Staff-Engineer-style pipeline
  — analyze (bug_fixer agent) → propose a patch (engineer agent, staged
  only, never live) → QA review → Security review (deterministic secret/
  dangerous-pattern scan + a summary) → CEO approval → `--confirm`'d apply
  (backs up the original first) → run the test suite → verified/regressed.
  **The bug_fixer agent never touches the live codebase itself** — see
  `orchestrator/bugfix_tools.py` for why that boundary is enforced in code,
  not just convention: read access to real source, write access only to
  `.bugfixes/<id>/` staging.
- **Severity model**: P0 (critical) – P4 (trivial), not free-text labels.
- **Recurrence tracking**: a new finding at the same (file, function) as an
  earlier bug is linked as a recurrence, not tracked as an independent
  duplicate — the original's `occurrence_count` increments instead.
- **Regression tracking**: a bug that was `verified` and later fails tests
  again increments `regression_count` and flips back to `regressed` —
  distinct from a first verification attempt simply failing.
- **Patch Registry** (`patches` table): every proposal attempt kept (not
  overwritten), each with a full corrected file AND a human-reviewable
  unified diff, generated with stdlib `difflib` — see `--patches`.
- **Full-codebase Audit** (`orchestrator/audit.py`): CEO opens the audit →
  deterministic static analysis (Python's own `ast` module, not regex
  guessing, for the checks where correctness matters) across
  `orchestrator/**/*.py` for duplicate code, security patterns, nested-loop
  performance heuristics, missing error handling, dead code, unused files,
  and missing test coverage → Security's existing permission/audit-log
  review → the top N most severe findings deepened through the full Bug
  Fixer pipeline (bounded — not all ~50+ findings get a full LLM pass) →
  CEO executive summary. **Does not cover the TypeScript dashboard** — a
  Python `ast` analyzer has nothing to say about TypeScript; that would
  need a different toolchain (eslint, `tsc --noEmit`), not built here.
- **Bug/Audit alerts**: Telegram gets exactly three audit-related triggers
  — critical (P0/P1) findings, security findings, and completed fixes —
  not full audit reports (those go to the "Audit History" Sheets tab).
- Two real infrastructure bugs found and fixed while building this: a
  socket-read timeout raised a bare `TimeoutError` that wasn't caught by
  the existing `except URLError` clause (crashed instead of degrading
  cleanly), and the local-model timeout itself was too tight for `gemma4`'s
  real observed latency (raised 180s → 420s). One bug the audit's own
  missing-error-handling check found in this same session's code
  (`bug_fixer.run_tests` had no try/except around its subprocess call) —
  fixed and it's now a clean example run through `--bug-report`.

## Bug Fixer & Audit usage

```bash
# File a bug manually, or find candidates from real logs
python3 -m orchestrator.cli --bug-report "Title" --description "..." --severity P1
python3 -m orchestrator.cli --bug-scan                 # list candidates from failed tasks / error_log
python3 -m orchestrator.cli --bug-analyze-scan          # scan AND create+analyze every candidate

python3 -m orchestrator.cli --bug-analyze 1              # root-cause analysis only
python3 -m orchestrator.cli --bug-propose 1               # engineer proposes a staged patch + diff
python3 -m orchestrator.cli --bug-review 1                 # propose -> QA -> Security -> CEO in one call

python3 -m orchestrator.cli --bug-list --bug-status open
python3 -m orchestrator.cli --bug-detail 1                  # full Bug Report / RCA / Risk / Patch / Test Results
python3 -m orchestrator.cli --patches --patch-bug 1

# Only after CEO approval -- explicit --confirm required, backs up the original first
python3 -m orchestrator.cli --bugfix-apply 1 --confirm
SHAKTHI_ALLOW_EXEC=1 python3 -m orchestrator.cli --bugfix-test 1

# Full codebase audit: CEO -> Security -> Bug Fixer -> Engineer -> CEO
python3 -m orchestrator.cli --audit-run --deepen 3
```

`--bugfix-apply` refuses to run without a prior `ceo_approved` status and
without `--confirm` — there is no path from "bug filed" to "live code
changed" that skips both gates.

---

# Phase 0.3 (still current)

- **Web dashboard** (`dashboard/`, Next.js + TypeScript + Tailwind, dark
  mode default): 12 nav entries. **6 fully wired to real data** — Executive
  Dashboard, Agent Registry, CEO, Finance, Security, Cost Ledger — plus
  **Website Monitoring** (real, checks local file presence). **5 are
  explicitly marked "soon"** in the nav (Task Pipeline, Agent Health
  Monitor, Memory Explorer, Knowledge Explorer, Workspace Manager) rather
  than faked — see each page for exactly what's missing and why.
- **Google Sheets** (`orchestrator/sheets.py`) is now the official business
  ledger: 8 tabs (Daily Summary, Revenue Ledger, Expense Ledger, P&L
  Statement, Tax Register, AI Cost Ledger, Website Health, CEO Decision
  Log), append-only with a local sync cursor, real numbers from
  `calculations.py` (profit, operating margin, estimated tax, ROI, cash
  flow). **Not exercised against a live spreadsheet in this build** — no
  Google service account was available. The row-building logic is unit
  tested (`tests/test_calculations.py`); the actual API calls are real,
  correct Sheets API v4 calls, unverified end-to-end. See "Google Sheets
  setup" below.
- **Telegram behavior changed**: the automated/scheduled path
  (`scheduled_reports.py`, meant for cron) **no longer sends full reports**
  — it syncs Sheets, then runs an alert sweep for six categories only
  (revenue, security, website downtime, agent failures, critical CEO
  decisions — "new orders" is the same signal as revenue, this system has
  no separate order entity). A founder can still pull one full report
  on demand with `--telegram-send`; that's a person asking, not the
  automated path pushing.
- **Telegram commands**: `/status /ceo /finance /security /costs /agents
  /websites /projects /memory /health` via `--telegram-poll`.
- Credentials for both Telegram and Sheets are **manual entry every call**
  (`--telegram-token`/`--telegram-chat-id`, `--sheets-credentials`/
  `--sheets-id`) — never written to a stored config file, per your stated
  preference that these change frequently. An env var fallback exists
  purely as a cron convenience, never the primary path.
- `finance_entries` gained a `category` column (general/marketing/hosting/
  tools/payroll/...) so Marketing Cost is a real, separately trackable
  number, not folded into general expenses.

---

# Phase 0.2 (still current)

Phase 0.2 added real capability on top of the Phase 0.1 loop: a
permission-gated tool system (file read/write, sandboxed command execution),
full audit logging, a deterministic Website Builder, and CEO/Finance/Security
governance workflows with a CLI dashboard.

## What's new in Phase 0.2

- **Tool system** (`orchestrator/tools/`): `read_file`/`write_file`/`list_dir`
  scoped to a per-business workspace with path-containment checks (blocks
  `..` traversal, absolute-path injection, symlink escapes — see
  `tests/test_tools.py`), and `run_command` (argv-allowlisted, no shell,
  timeout, minimal env). Every call — allowed or denied — is logged to
  `tool_calls`. **`run_command` is granted to zero agents by default** and
  additionally requires `SHAKTHI_ALLOW_EXEC=1` — built, wired, tested; not
  switched on.
- **Website Builder foundation** (`orchestrator/sitegen.py`): deterministic
  template rendering + write, through the same tool-execution path model-
  driven calls use. Doesn't depend on a local model reliably emitting a tool
  call. Run: `python3 -m orchestrator.cli --generate-site --business 1`
- **CEO** (`orchestrator/ceo.py`): scores a goal 1-10 on priority/risk/
  business-impact and returns approved/rejected/revise. Fails closed to
  `revise` if its output can't be parsed — never silently approves.
- **Finance** (`orchestrator/finance.py`): daily/weekly/monthly reports from
  real `cost_ledger` and `finance_entries` data, including actual Ollama-vs-
  Claude savings. No billing integration exists — revenue/expense are
  whatever you log via `--finance-entry`.
- **Security** (`orchestrator/security.py`): deterministic checks (secret
  patterns, permission/audit review, site-risk heuristics) — not a local
  model's judgment call.
- **Dashboard**: `--dashboard` is a **CLI report**, not a web UI. No frontend
  exists yet; building one is a distinct, larger effort than everything
  else in this phase.

## Why SQLite, not Postgres

The v1/v2 architecture doc specifies Postgres + pgvector. This machine has
no Docker and no Postgres installed, but it does have Ollama running with
`llama3.2` and `gemma4` already pulled — so Phase 0.1 runs on SQLite +
Python stdlib with **zero setup**, to prove the routing/memory/cost loop
today instead of waiting on infra. Table shapes match the Postgres design
1:1 (including `tenant_id` on every row), so moving to Postgres later is a
data migration, not a redesign.

## Known gaps

- No row-level security / tenant enforcement — fine for one founder on one
  machine, not fine once this runs multi-business traffic on shared infra.
- Memory retrieval is recency-only, not embedding similarity — upgrade path
  is `nomic-embed-text` via Ollama, or pgvector after the Postgres move.
- Single process, single SQLite file — fine for one founder's task volume,
  not for 100 agents running concurrently. Postgres + a real worker pool is
  a later move.
- `run_command`'s sandbox is real but partial: argv allowlist + no shell +
  timeout + minimal env stop shell injection and env leakage, but don't
  bound what an allowlisted interpreter does once invoked (`python3
  <script>` is unrestricted code execution regardless of argv shape). Real
  containment needs a container/VM sandbox — out of scope until this leaves
  a bare laptop. macOS `sandbox-exec` was evaluated and dropped (noisy,
  undocumented profile grammar) — see `orchestrator/tools/exec_tools.py`.
- `classify_risk()`'s critical-keyword matching is substring-based, not
  word-boundary — e.g. "no contracts needed" matches "contract" and gets
  classified critical. Known bluntness, not fixed in this phase.
- **`propose_patch()`'s full-file regeneration reliably times out (420s)
  on this hardware for at least one real file** (`tests/test_bug_fixer.py`)
  — reproduced twice, identically, to the second. The Engineer agent is
  asked to output an entire corrected file; generation time scales with
  output length, and gemma4 generating ~100 lines of Python on a CPU-bound
  laptop is genuinely slow. `run_full_audit()` is resilient to this now
  (a per-finding failure no longer crashes the whole audit — that WAS a
  real crash, fixed live during this phase, see `db.fail_audit`), but the
  underlying slowness isn't fixed. Real fix: ask for a targeted diff
  instead of a full-file rewrite, or use a smaller/faster model for this
  specific step — not implemented yet.
- The CEO agent's role_prompt is format-locked to its json decision-block
  by default strongly enough that a differently-shaped request (like the
  audit's free-form executive summary) came back as the wrong format on
  the first real run — fixed by making the override instruction explicit
  in the prompt (see `audit.py`'s summary_prompt), verified working after
  the fix, but this is a real illustration of how rigid a small model's
  system-prompt adherence can be.
- The CEO agent's structured-JSON output is validated by the QA agent (a
  3B local model) judging goal-semantics, not JSON-format compliance — in
  practice this makes CEO decisions escalate to Claude more often than
  they should. The fail-closed behavior (default to `revise` if unparseable,
  never silently approve) is correct; the QA/CEO prompt fit is not tuned.
- No auth, secrets management, or deployment pipeline — not in scope for
  any phase so far.

## Setup

```bash
cd shakthi-os
python3 -m pip install -r requirements.txt
python3 -m orchestrator.cli --init          # creates shakthi.db, registers all 11 agents
python3 -m orchestrator.seed                # seeds 10 businesses + 100 sites
python3 -m orchestrator.cli --list-agents
python3 -m unittest discover tests          # path containment, permission, sandbox tests
```

## Running a task

```bash
python3 -m orchestrator.cli --agent manager "Plan the launch of a landing page for Business 01" --business 1
python3 -m orchestrator.cli --agent engineer "Write a Python function that validates an email address" --business 1
python3 -m orchestrator.cli --agent sales "Draft a cold outreach email for a local bakery" --business 2
```

Run the same agent twice on related goals and the second call's memory
context will include a summary written by the Memory agent from the first —
that's the retrieval loop working.

## Checking cost

```bash
python3 -m orchestrator.cli --costs
```

Should show `ollama` calls at `$0.0000` and, if `ANTHROPIC_API_KEY` is unset,
zero `claude` rows — nothing escalates without an explicit key.

## Enabling cloud escalation (optional)

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-...
```

Anything classified `critical` (refunds, contracts, "delete all", etc. — see
`orchestrator/routing.py`) routes straight to Claude; anything that fails
the QA agent's local review escalates once. Without the key, both paths
return the local best-effort result with a note instead of crashing.

## CEO, Finance, Security, Website Builder

```bash
# CEO: score and decide on a proposed goal
python3 -m orchestrator.cli --decide "Launch a $15/mo subscription tier" --business 1

# Finance: log real numbers, then report
python3 -m orchestrator.cli --finance-entry revenue --amount 500 --business 1 --note "first client payment"
python3 -m orchestrator.cli --finance-entry expense --amount 40 --business 1 --note "domain + hosting"
python3 -m orchestrator.cli --finance-report monthly --business 1

# Security: deterministic secret/permission/site-risk scan
python3 -m orchestrator.cli --security-review --business 1

# Website Builder: deterministic template render + write
python3 -m orchestrator.cli --generate-site --business 1

# Everything at once
python3 -m orchestrator.cli --dashboard
python3 -m orchestrator.cli --audit 20        # tool_calls audit log
python3 -m orchestrator.cli --list-tools
```

## Enabling command execution (optional, off by default)

```bash
export SHAKTHI_ALLOW_EXEC=1
```

Even then, no agent is granted `run_command` in its yaml by default — you'd
also add it to an agent's `allowed_tools` deliberately. Two gates deep on
the one genuinely dangerous tool, on purpose.

## Adding the 12th–100th agent

Write a new `agents/<id>.yaml` (see the existing 11 for the shape), then:

```bash
python3 -m orchestrator.cli --init
```

No code changes — this is the mechanism that's supposed to make 100 agents
tractable.

## Web dashboard

One command starts both (API + Next.js dev server), in the background,
logging to `logs/api.log` and `logs/dashboard.log`. Idempotent — safe to
re-run; it won't start a second copy if either is already up on its port:

```bash
./start_dashboard.sh                 # http://localhost:3000, http://127.0.0.1:8787
./stop_dashboard.sh                  # stops both
```

Or run them separately, one per terminal, if you want to watch their
output live instead of tailing the log files:

```bash
# terminal 1 — the API the dashboard reads from
cd shakthi-os
python3 -m orchestrator.api          # http://127.0.0.1:8787

# terminal 2 — the dashboard itself
cd shakthi-os/dashboard
npm install                          # first time only
npm run dev                          # http://localhost:3000
```

Both must be running — the dashboard is a thin client over the API, it has
no data of its own. If a page shows "API unreachable," the API server isn't
running or died; restart it (it must be started from the `shakthi-os`
directory, not `dashboard/`, or the `orchestrator` package won't be found).

No auth on either server — both assume a trusted local operator, same as
the CLI. Do not expose port 8787 or 3000 beyond localhost without adding
one first.

## Telegram setup

1. Message [@BotFather](https://t.me/BotFather) on Telegram, `/newbot`, get a token.
2. Message your new bot once, then find your chat_id (e.g. via `https://api.telegram.org/bot<TOKEN>/getUpdates` after messaging it).
3. Everything takes the token/chat_id as flags — nothing is saved to disk:

```bash
python3 -m orchestrator.cli --telegram-test --telegram-token "123:ABC" --telegram-chat-id "5551234"
python3 -m orchestrator.cli --telegram-send ceo --telegram-token "123:ABC" --telegram-chat-id "5551234"
python3 -m orchestrator.cli --alerts-sweep --telegram-token "123:ABC" --telegram-chat-id "5551234"
python3 -m orchestrator.cli --telegram-poll --telegram-token "123:ABC" --telegram-chat-id "5551234"   # runs /commands, foreground
```

**Not verified live in this build** — no bot token was available. The
report-generation and command-routing logic is tested offline
(`report_generators.py`, `telegram_service.handle_command`); the actual
`sendMessage`/`getUpdates` HTTP calls are real, correct Bot API v1 calls,
unverified end-to-end. Run `--telegram-test` first once you have a token —
treat it as the verification step.

## Google Sheets setup

1. In Google Cloud Console: create a project (or use one), enable the
   **Google Sheets API**, create a **Service Account**, generate a JSON key.
2. Create a Google Sheet, share it with the service account's email
   (found in the JSON key file) as **Editor**.
3. Copy the spreadsheet ID from its URL (`.../d/<THIS PART>/edit`).

```bash
pip install -r requirements.txt   # google-api-python-client + google-auth now included
python3 -m orchestrator.cli --sheets-sync \
  --sheets-credentials /path/to/service-account.json \
  --sheets-id "1AbC...xyz" \
  --sheets-period monthly \
  --tax-rate 0.18
```

Creates all 8 tabs if missing, writes headers, appends new rows since the
last sync (tracked in `.sheets_sync_state.json`, gitignored). Safe to
re-run — ledgers never duplicate rows, snapshot sheets (Daily Summary, P&L,
Tax Register, Website Health) append one fresh row per business per run.

`--tax-rate` is a fraction (0.18 = 18%). **The Tax Register is an estimate,
not a filed calculation** — no jurisdiction logic, no deductions, no GST
input credits. It exists so the number is there to review with an actual
accountant, not to replace one.

**Not exercised against a live spreadsheet in this build** — no service
account was available. Treat the first real `--sheets-sync` as the
verification step; check `ensure_structure` created all 8 tabs correctly
before relying on it.

## Automating it (cron)

```cron
# Daily, 7am: sync Sheets + run the alert sweep. Full reports do NOT go to Telegram.
0 7 * * * cd /path/to/shakthi-os && python3 -m orchestrator.scheduled_reports \
  --period daily --sheets-credentials /path/to/sa.json --sheets-id "1AbC...xyz" \
  --telegram-token "123:ABC" --telegram-chat-id "5551234" >> logs/daily.log 2>&1

# Weekly / monthly / quarterly / yearly: same command, different --period
0 7 * * 1 cd /path/to/shakthi-os && python3 -m orchestrator.scheduled_reports --period weekly ... 
0 7 1 * * cd /path/to/shakthi-os && python3 -m orchestrator.scheduled_reports --period monthly ...
```

Credentials in a crontab are the one place "manual entry every time" isn't
practical — put them directly in the crontab line (root-only readable,
`crontab -e`), not in a file this repo tracks.
