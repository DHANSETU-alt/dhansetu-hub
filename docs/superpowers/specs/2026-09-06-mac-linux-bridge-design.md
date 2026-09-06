# Mac–Linux Bridge: Single Control-Plane, Two-Node Execution

## Context

Shakthi_OS currently runs as two disconnected instances:

- **Linux PC** (dedicated 24/7 host, acquired per [[project_linux_to_drive_migration_plan]]): running Shakthi_OS 3.2, with its own `shakthi.db`, its own `orchestrator/api.py`, its own dashboard.
- **This Mac**: running Shakthi_OS 3.1, with its own separate `shakthi.db` and its own local API server (started ad hoc this session while troubleshooting the dashboard).

The founder wants both machines working as one system — "same OS, double brain" — with the Linux box as the control-plane (matching its original reliability rationale: it was built specifically to be the stable 24/7 machine, freeing the Mac from continuous-duty work). This spec covers connecting the two into a single shared brain, not two databases syncing.

Confirmed with the founder:
- Both machines are on the same LAN right now; no SSH link exists between them yet.
- Linux is control-plane; Mac contributes as a second execution node.
- SSH trust will be established via a fresh keypair generated on the Mac, with the founder appending the public key to the Linux box's `authorized_keys`.
- Linux's 3.2 is the same git history as Mac's 3.1, just further ahead — a fast-forward is expected, not a divergent merge.

Mac's local repo currently has 5 modified files and 2 untracked paths (in-progress Task/Project-track dashboard work), and no git remote configured.

## Goals

1. One shared source of truth: Linux's `shakthi.db` becomes the only database. Mac's local database is archived, not deleted, and Mac stops running its own control plane.
2. Mac's codebase is brought up to parity with Linux's 3.2 via a normal git fast-forward, without losing Mac's in-progress uncommitted work.
3. Mac can execute agent work (using its own local Ollama models) against Linux's shared task queue via the existing `orchestrator/routing.run_task` API — a second real execution node, not a read-only viewer.
4. The existing `ceo.py` and `pa_angella.py` agents keep living once, on Linux, as the shared brain both machines dispatch into.
5. Everything is additive and reversible: no destructive git operations, no data deleted, connection removable by deleting the SSH key and git remote.

## Non-goals

- No peer-to-peer / no-master architecture (explicitly rejected by the founder in favor of Linux-as-control-plane).
- No automatic conflict-resolution engine for divergent databases — there is deliberately only one database going forward, so this class of problem doesn't arise.
- No public/internet-facing exposure of either machine's API — LAN-only (or LAN + Tailscale if the LAN link proves unreliable later; not needed for this pass since both machines are confirmed on the same network now).
- Not building the specific revenue/"money-printing" task content in this pass — this spec is the bridge only. Once connected, task dispatch for actual goals happens through the existing `routing.run_task` flow, unchanged.

## Architecture

```
┌─────────────────────────────┐         SSH (git fetch)        ┌─────────────────────────────┐
│   Linux PC (control-plane)  │◄────────────────────────────────│   Mac (execution node)      │
│                              │                                 │                              │
│  orchestrator/api.py :8787  │◄──── HTTP (routing.run_task) ───│  orchestrator/cli.py         │
│  shakthi.db  (single DB)    │                                 │  local Ollama models         │
│  ceo.py / pa_angella.py     │─────  results posted back  ────►│  (no local shakthi.db writes)│
│  dashboard :3000            │                                 │                              │
└─────────────────────────────┘                                 └─────────────────────────────┘
```

Linux is unchanged in role: it keeps running exactly what it runs today. The only new thing on Linux is one appended line in `~/.ssh/authorized_keys`.

Mac changes role from "independent instance" to "client + execution node":
- `API_BASE` (see `dashboard/lib/api.ts` and any CLI equivalent) is repointed from `http://127.0.0.1:8787` to `http://<linux-lan-ip>:8787`.
- Mac's own `orchestrator/api.py` and dashboard dev server (started this session) are stopped — Mac no longer runs a second control plane.
- Mac's local `shakthi.db` is renamed/archived (e.g. `shakthi.db.mac-pre-bridge-2026-09-06.bak`), not deleted, so nothing already tracked there is lost if it needs to be recovered or manually reconciled later.

## Data flow

1. Founder or Claude on either machine calls `routing.run_task(agent_id, goal, business_id)`.
2. On Mac, this now goes over HTTP to Linux's `orchestrator/api.py` (new thin client wrapper) instead of Mac's local `db` module directly.
3. Linux's API inserts the task into the single `shakthi.db`, dispatches to the named agent (`ceo`, `pa_angella`, or any of the existing roster) exactly as it does today for locally-originated tasks.
4. If the task is one Mac should physically execute (e.g. needs a Mac-only tool, or the founder wants to spread load using Mac's local Ollama models), Linux's dispatch marks it for the `mac` executor. Mac polls a Linux endpoint (`GET /api/tasks?executor=mac&status=pending`, new but small addition to `orchestrator/api.py`) on a short interval, runs any matching task locally, and posts the result back via `POST /api/tasks/<id>/result` — Linux's DB remains the only place results are recorded.
5. The dashboard (served from Linux, or from Mac purely as a viewer pointed at Linux's API) shows one unified task/initiative history regardless of which machine did the work.

## Setup steps (implementation-level, covered in detail by the plan)

1. **Commit Mac's in-progress work first.** The 5 modified files + `SmartCopyButton.tsx` + `state/` are real in-progress work (Task/Project-track dashboard changes) and must be committed before any fetch/merge, so a fast-forward can't touch them or get blocked by them.
2. **Generate a dedicated SSH keypair on Mac** (e.g. `~/.ssh/shakthi_bridge_ed25519`) — separate from the existing `github_shakthi_os` deploy key, since that key has a different, narrower trust scope (GitHub only).
3. **Founder appends the new public key** to the Linux box's `~/.ssh/authorized_keys` (one command, given at execution time).
4. **Add Linux as a git remote** on Mac (`git remote add linux ssh://<user>@<linux-ip>/path/to/shakthi-os`), `git fetch linux`, then fast-forward `main` — expected to be a clean fast-forward since Linux is confirmed to be the same history, further ahead.
5. **Archive Mac's local `shakthi.db`**, stop Mac's local `orchestrator/api.py` and dashboard dev server.
6. **Point Mac's config at Linux's API** (`API_BASE=http://<linux-lan-ip>:8787`), verify `/api/health` responds.
7. **Round-trip validation**: dispatch one real low-risk task from Mac's CLI, confirm it appears in Linux's dashboard/db, confirm any result posts back correctly.

## Error handling / failure modes

- **Linux unreachable from Mac** (network drop, Linux off): Mac's client calls fail closed with a clear error (existing `ApiError` in `dashboard/lib/api.ts` already does this) — Mac does not fall back to a local database silently, since that would recreate the two-brain-drift problem this spec exists to remove. Founder is told plainly "Linux control-plane unreachable" rather than Mac quietly operating standalone.
- **Git fast-forward is not clean** (unexpected divergence found once actually fetching): stop and report the actual `git log --oneline linux/main..main` / `main..linux/main` diff to the founder before doing anything else — do not force-push, do not discard either side's commits.
- **SSH key rejected**: verify the exact public key content and target path with the founder rather than retrying blindly or falling back to password auth.

## Testing

- Real round-trip task dispatch (Mac → Linux DB → Linux dashboard → result back to Mac), as in setup step 7.
- Confirm existing test suites still pass on both machines' checked-out code after the fast-forward (`pytest`, `tsc --noEmit` per prior session's own bar for "real" — see [[project_linux_to_drive_migration_plan]]).
- Confirm Mac's dashboard, when pointed at Linux's API, renders live Linux data (not a stale/cached local copy).

## Rollback

Every step is reversible: remove the git remote, delete `shakthi_bridge_ed25519` from Mac and its entry from Linux's `authorized_keys`, restore Mac's archived `shakthi.db` and repoint `API_BASE` back to `127.0.0.1:8787` to return Mac to a fully standalone instance.
