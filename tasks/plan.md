# Implementation Plan: DhanSetu Hub Consolidation and MacBook Hosting

## Overview

Consolidate the existing `/Users/apple/shakthi-os` working tree into the single canonical DhanSetu Hub application, preserving all legitimate data and unfinished work. Deliver the product and founder operations scope in reversible vertical slices, then migrate durable state to the external SSD and switch `dhansetuhub.in` only after production-like verification and rollback readiness.

## Current Authority and Safety Decisions

- Canonical working repository: `/Users/apple/shakthi-os` at `c788dbfce515760fbc33eb7faa0b87599ab75acc` on `main`, with substantial pre-existing uncommitted work that must be preserved.
- Current database authority: `/Users/apple/shakthi-os/shakthi.db` via `SHAKTHI_DB_PATH`; SQLite integrity check passes and reports 59 tables.
- `/Users/apple/shakthi-os/dhansetu-web` is a nested two-page Git repository and a provisional migration source, not the replacement workspace.
- `/Users/apple/claude-code` is an unrelated upstream tooling repository and is protected from modification or cleanup.
- External SSD `/dev/disk2s1` is a 240.1 GB Linux partition that macOS cannot currently mount. Do not erase or reformat it automatically.
- No cleanup, migration, production service activation, DNS cutover, or destructive database change may happen until a verified SSD backup and sample restore exist.
- Existing Cloudflare/Sites hosting remains live until the MacBook deployment passes all gates and has a tested rollback.

## Architecture Decisions

- Preserve the existing Python orchestrator, Next.js dashboard, SQLite history, and public route behavior until evidence supports an incremental migration.
- Keep SQLite unless current production evidence proves another database is authoritative; do not introduce PostgreSQL merely for preference.
- Move durable state behind explicit SSD-root configuration and fail closed when the expected volume identity is missing.
- Remove browser-supplied payment secrets and use server-defined product IDs/amounts before exposing payment routes.
- Add server-enforced identity and founder authorization before building private dashboard surfaces.
- Use feature flags for incomplete product work and keep production empty states honest.
- Use launchd only after local production commands, SSD gates, backup/restore, and health checks pass.

## Dependency Order

1. Preserve and baseline the current system.
2. Repair critical secret/payment/auth boundaries.
3. Establish one product/domain/data vocabulary and migrate legacy identifiers safely.
4. Build vertical product slices with tests.
5. Build founder metrics from verified event sources.
6. Add bounded research/editorial automation.
7. Provision SSD-backed runtime, launchd, HTTPS, monitoring, and rollback.
8. Cut over traffic only after acceptance evidence.

## Task List

Tasks and checkpoints are tracked in `tasks/todo.md`.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Dirty tree contains unfinished founder work | High | Preserve exact state; no resets or bulk cleanup; archive before edits that overlap it |
| Payment secret accepted from browsers | Critical | Disable/fix first; server-only credentials; fixed product catalog; signature and retry tests |
| Telegram credential embedded in cron/process args | Critical | Redact, remove inline secret after backup, rotate through owner-controlled channel |
| SSD is Linux-formatted and unmounted on macOS | High | Do not format; identify intended data/history and choose a compatible migration with owner approval if destructive formatting would be required |
| Existing public app is split across Sites/Cloudflare and local code | High | Inventory routes/data first; preserve live hosting until parity and rollback pass |
| Existing lint/build failures hide regressions | Medium | Record baseline, fix in narrow slices, enforce build/lint/test gates afterward |
| Automated financial/legal publishing causes harm | High | Versioned deterministic rules, official sources, review gates, fail-closed automation |
| Legacy cron/launchd creates duplicate jobs | High | Inventory exact jobs, disable only after replacement scheduler is verified |

## Open External Actions

- Make the external SSD accessible to macOS without erasing existing data, or approve a separately backed-up reformat only after its contents are identified.
- Rotate the exposed Telegram bot token in BotFather; never send the replacement through chat.
- Later, complete account-holder-only OAuth, Razorpay test, DNS, and social-platform consent actions when implementation is ready.

