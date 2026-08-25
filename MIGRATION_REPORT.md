# SHAKTHI OS — Migration Report

Generated: 2026-08-23, on macOS (source machine), for migration to Ubuntu 24.04 LTS.
Scope: `/Users/apple/shakthi-os` — full project scan, real numbers below (`du`, `find`, `ollama list`, `sqlite3 .tables`), not estimates.

## 1. Project Structure

```
shakthi-os/                    1.1 GB total (988 MB is dashboard/node_modules + dashboard/.next —
│                               both are build artifacts, NOT backed up; see BACKUP_CHECKLIST.md)
├── agents/            15 .yaml persona files           60 KB
├── dashboard/                  Next.js 16.3.2 + TS dashboard
│   ├── app/            17 route folders, 27 .tsx files 132 KB (source only)
│   ├── components/      Sidebar, AutoRefresh, HealthChart, shadcn ui/     40 KB
│   ├── lib/              api.ts (typed fetch client), utils.ts           16 KB
│   ├── node_modules/    NOT backed up — restored via `npm install`       637 MB
│   └── .next/            NOT backed up — build cache, regenerated        481 MB
├── db/
│   └── schema.sql        all table definitions                          20 KB
├── orchestrator/          43 .py files — the whole backend               928 KB
│   └── tools/              file/exec sandbox, permission dispatch
├── templates/             1 website template (template_landing_v1)        4 KB
├── tests/                 8 test files, 144 tests total                  192 KB
├── shakthi.db             SQLite — all runtime data                     236 KB
├── requirements.txt       Python deps
├── start_dashboard.sh / stop_dashboard.sh
├── PROJECT_STATUS.md, README.md
├── .git/                  full commit history (1 commit as of this report) 876 KB
└── workspaces/            per-business generated sites — currently near-empty  12 KB
```

**Essential backup size (source + data, excluding node_modules/.next/__pycache__): ~2.5 MB.**
Ollama model weights (11.6 GB) are separate — see §9, not filed with the project backup.

## 2. Installed Features

Built across this project's history, in order:
- **Phase 0.1–0.2**: local orchestrator (SQLite, Ollama routing with one-time Claude escalation), permission-gated tool system (file read/write, sandboxed command execution), Website template rendering foundation.
- **Phase 0.3**: Google Sheets as the business ledger (append-only, idempotent sync), Telegram as an alert-only channel (never full reports), Next.js dashboard.
- **Phase 0.4**: Bug Fixer (Staff-Engineer-style patch pipeline: propose → QA → Security → CEO approval → apply, with backup-before-write), full-codebase Audit (CEO → Security → Bug Fixer → Engineer → CEO).
- **SHAKTHI OS v4**: Sentinel (system health monitoring, real psutil), Buddy (Gujarati/Hindi/English family assistant, Safe Mode content filter), Voice Commander (wake-word detection, Owner/Family/Guest permission gating, CEO-in-the-loop only on critical-risk commands).
- **Website Builder Bot**: 7 site types, founder-request → CEO approval → requirements → build → QA → Security → deployment package pipeline.
- **WEB-001**: external website auditor (HTTPS, SEO, mobile, accessibility, security headers, broken links, sitemap/robots.txt — all deterministic checks against a live URL).
- **Correction Bot**: "Senior Reviewer" pipeline (Task Complete → Correction Review → QA Review → Security Review → Final Approval), hooked automatically onto Bug Fixer patches, Website Builder pipelines, and Audit executive summaries.
- **Founder Command Center dashboard**: 18 pages, glassmorphism UI, real charts (recharts), local JSON API server (`orchestrator/api.py`, stdlib `http.server`, no framework).

## 3. Agents (15, config-driven — `agents/*.yaml`, no code change needed to add one)

| id | layer | local model | allowed_tools |
|---|---|---|---|
| ceo | governance | (see yaml) | — |
| security | governance | llama3.2 | read_file, list_dir |
| qa | engineering | llama3.2 | — |
| bug_fixer | engineering | (see yaml) | file + staging tools |
| engineer | engineering | (see yaml) | file tools |
| website_builder | engineering | (see yaml) | file tools |
| correction_bot | governance | llama3.2 | — (review-only, no write access) |
| finance | business | (see yaml) | — |
| manager | business | (see yaml) | — |
| sales, customer_success, data_intelligence | business | (see yaml) | — |
| buddy | personal | (see yaml) | — |
| knowledge | personal | (see yaml) | — |
| memory | system | (see yaml) | — |

An agent is a YAML file loaded into the `agents` DB table by `registry.sync_registry()` (run via `cli --init`) — restoring on Linux just means the 15 files exist and `--init` has run.

## 4. Services (all local, no cloud dependency required)

| Service | Port | Started by | Auto-starts? |
|---|---|---|---|
| Ollama | 11434 | `Ollama.app` / `ollama serve` | Yes on macOS (launchd `com.ollama.ollama`) — **must be re-registered as a systemd service on Ubuntu**, see LINUX_MIGRATION_GUIDE.md |
| Shakthi API | 8787 | `python3 -m orchestrator.api` | No — `./start_dashboard.sh` |
| Dashboard (Next.js dev) | 3000 | `npm run dev` (via `start_dashboard.sh`) | No |

## 5. Dependencies

**Python** (`requirements.txt`, Python 3.14.6 on the source machine):
```
pyyaml>=6.0
google-api-python-client>=2.0
google-auth>=2.0
google-auth-httplib2>=0.2
truststore>=0.9        # OS trust store SSL bridge — fixes corporate-proxy cert failures
psutil>=6.0             # Sentinel real system metrics
faster-whisper>=1.0     # Voice Commander STT
sounddevice>=0.5
numpy>=1.24
tokenizers>=0.13
huggingface-hub>=0.21
tqdm
# anthropic>=0.40       # optional, only for Claude cloud escalation
```

**Dashboard** (`dashboard/package.json`):
```json
{
  "next": "16.3.2", "react": "19.2.8", "react-dom": "19.2.8",
  "@base-ui/react": "^1.7.0", "recharts": "^3.8.0", "shadcn": "^4.19.0",
  "class-variance-authority": "^0.7.1", "clsx": "^2.1.1",
  "lucide-react": "^1.33.0", "tailwind-merge": "^3.6.0", "tw-animate-css": "^1.4.0"
}
```
`node_modules/` (637 MB) is not backed up — `npm install` on Ubuntu rebuilds it from `package-lock.json`, which IS backed up (locks exact versions).

## 6. Telegram Setup

Bot created via @BotFather. Token/chat_id are **never stored to disk** — passed as CLI flags on every invocation (`--telegram-token`, `--telegram-chat-id`), by explicit founder requirement. Nothing to migrate here except re-entering the same credentials on the new machine when running a command.

**Verified live, this session** (not a stale claim — real deliveries): OPS-001 (Sentinel report), OPS-002 (Security posture report), WEB-001 (Website audit report), Correction Bot report. All confirmed delivered to the real configured chat. `README.md`'s "not verified live" note under Telegram setup is now outdated and should be corrected post-migration.

## 7. Google Sheets Setup

Service-account JSON key + spreadsheet ID, also passed as flags only, never stored (`--sheets-credentials`, `--sheets-id`). **Never exercised against a live spreadsheet this session** — no service account was available at any point. 11 tabs are defined in `orchestrator/sheets.py` (`SHEET_NAMES`), including "Correction History" (newest addition). Treat the first real `--sheets-sync` on the new machine as the verification step.

## 8. Database Requirements

- **Current**: SQLite, single file `shakthi.db` (236 KB), 21 tables (`agents`, `businesses`, `tasks`, `task_events`, `cost_ledger`, `memory_entries`, `tool_calls`, `decisions`, `finance_entries`, `security_reports`, `error_log`, `bugs`, `bug_events`, `patches`, `audits`, `audit_findings`, `system_health`, `knowledge_documents`, `buddy_log`, `voice_commands`, `website_projects`, `corrections`, `correction_findings`, `sites`).
- SQLite was a **deliberate stand-in for Postgres** — every row already carries `tenant_id`/`business_id` for that eventual migration. `db/schema.sql` is the single source of truth; SQLite-specific syntax is minimal (`AUTOINCREMENT`, `CURRENT_TIMESTAMP` defaults — both have direct Postgres equivalents).
- **This migration is macOS → Ubuntu, not SQLite → Postgres** — no DB engine change is in scope. Restoring `shakthi.db` as-is (bit-for-bit file copy) is sufficient; SQLite is fully portable across OSes.
- `LINUX_MIGRATION_GUIDE.md` includes an optional PostgreSQL setup section per your request, in case you want to do the engine migration at the same time — that is a separate, larger undertaking than the OS migration and is called out as optional there.

## 9. Ollama Requirements

```
$ ollama list
NAME               ID              SIZE      MODIFIED
llama3.2:latest    a80c4f17acd5    2.0 GB    5 weeks ago
gemma4:latest      c6eb396dbd59    9.6 GB    2 months ago
```
Total 11.6 GB. **Not included in the project backup** (too large for the 7.9 GB external drive, and trivially re-downloadable). On Ubuntu: `ollama pull llama3.2` and `ollama pull gemma4` after installing Ollama — see LINUX_MIGRATION_GUIDE.md §2.

`llama3.2` (fast, 3B) is used for most agents; `gemma4` (slow, 9.6 GB, CPU-bound — observed 2:24–3:26 per call on this machine) is used where noted in individual `agents/*.yaml` files. `OLLAMA_TIMEOUT_SECONDS` is set to 420 in `config.py` specifically to accommodate `gemma4`'s real observed latency.

## 10. Dashboard Components

17 route pages (`dashboard/app/*/page.tsx`) + `app/page.tsx` (Executive Dashboard). Shared components: `Sidebar.tsx` (nav), `AutoRefresh.tsx`, `HealthChart.tsx`, `components/ui.tsx` (Card/Badge/StatTile/EmptyState), `components/ui/{badge,button,card,chart}.tsx` (shadcn). All pages are React Server Components fetching from the local API (`lib/api.ts`, `API_BASE` defaults to `http://127.0.0.1:8787`) — no client-side state beyond `AutoRefresh`'s polling.

## Startup Instructions (current, macOS — see LINUX_MIGRATION_GUIDE.md for the Ubuntu version)

```bash
cd ~/shakthi-os
./start_dashboard.sh          # starts API (:8787) + dashboard (:3000) in background
# open http://localhost:3000
./stop_dashboard.sh           # stops both
```
Ollama auto-starts on macOS login (launchd). Claude Code itself: `cd ~/shakthi-os && claude`.
