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
6. **Mac works as a true remote terminal from any network, not just the home LAN.** The founder must be able to check status or dispatch a command from the Mac while away from home and have it reach Linux.
7. **Zero status drift, structurally.** Mac never computes or stores its own percent-complete/status for any initiative or task — every read (CLI, dashboard, terminal query) goes live to Linux's API. There is exactly one number for any given task's status, not two numbers that are supposed to match.

**Concrete acceptance scenario (founder's own example):** founder asks on the Mac "what is Task 12's status" → answer comes from Linux's live DB. Founder says "start finishing Task 12" on the Mac → the actual work is dispatched to and executed on Linux. Mac's own status display for Task 12 updates to match Linux immediately after, because it was reading Linux's number all along, not a locally cached one.

## Non-goals

- No peer-to-peer / no-master architecture (explicitly rejected by the founder in favor of Linux-as-control-plane).
- No automatic conflict-resolution engine for divergent databases — there is deliberately only one database going forward, so this class of problem doesn't arise.
- No public/internet-facing exposure of either machine's API to the raw internet — reachability from any network is provided by Tailscale (a private mesh VPN, each machine gets a stable private IP reachable from anywhere once both are enrolled), not by port-forwarding Linux's API to the open internet.
- Not building the specific revenue/"money-printing" task content in this pass — this spec is the bridge only. Once connected, task dispatch for actual goals happens through the existing `routing.run_task` flow, unchanged.

## Architecture

```
              (both machines enrolled in one private Tailscale network --
               reachable from any location Mac happens to be on)

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
- Both machines are enrolled in a private Tailscale network, giving Linux a stable Tailscale IP reachable from Mac on any network (home, mobile hotspot, elsewhere).
- `API_BASE` (see `dashboard/lib/api.ts` and any CLI equivalent) is repointed from `http://127.0.0.1:8787` to `http://<linux-tailscale-ip>:8787`.
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
2. **Install and enroll Tailscale on both machines**, so each gets a stable private IP reachable from any network. This replaces plain LAN IPs for every subsequent step.
3. **Generate a dedicated SSH keypair on Mac** (e.g. `~/.ssh/shakthi_bridge_ed25519`) — separate from the existing `github_shakthi_os` deploy key, since that key has a different, narrower trust scope (GitHub only).
4. **Founder appends the new public key** to the Linux box's `~/.ssh/authorized_keys` (one command, given at execution time).
5. **Add Linux as a git remote** on Mac over its Tailscale address (`git remote add linux ssh://<user>@<linux-tailscale-ip>/path/to/shakthi-os`), `git fetch linux`, then fast-forward `main` — expected to be a clean fast-forward since Linux is confirmed to be the same history, further ahead.
6. **Archive Mac's local `shakthi.db`**, stop Mac's local `orchestrator/api.py` and dashboard dev server.
7. **Point Mac's config at Linux's API** (`API_BASE=http://<linux-tailscale-ip>:8787`), verify `/api/health` responds from Mac while off the home network (e.g. phone hotspot) to prove the "from anywhere" requirement.
8. **Add the `executor=mac` polling endpoint** to `orchestrator/api.py` on Linux (see Data flow step 4) and a small poll loop on Mac.
9. **Round-trip validation**: from the Mac, ask for Task 12's live status (confirm it now matches Linux exactly, not the 100%/`done` value currently cached in Mac's own soon-to-be-archived local db), dispatch one real low-risk task, confirm it appears in Linux's dashboard/db, confirm any result posts back correctly.

## Error handling / failure modes

- **Linux unreachable from Mac** (network drop, Linux off): Mac's client calls fail closed with a clear error (existing `ApiError` in `dashboard/lib/api.ts` already does this) — Mac does not fall back to a local database silently, since that would recreate the two-brain-drift problem this spec exists to remove. Founder is told plainly "Linux control-plane unreachable" rather than Mac quietly operating standalone.
- **Git fast-forward is not clean** (unexpected divergence found once actually fetching): stop and report the actual `git log --oneline linux/main..main` / `main..linux/main` diff to the founder before doing anything else — do not force-push, do not discard either side's commits.
- **SSH key rejected**: verify the exact public key content and target path with the founder rather than retrying blindly or falling back to password auth.

## Testing

- Real round-trip task dispatch (Mac → Linux DB → Linux dashboard → result back to Mac), as in setup step 7.
- Confirm existing test suites still pass on both machines' checked-out code after the fast-forward (`pytest`, `tsc --noEmit` per prior session's own bar for "real" — see [[project_linux_to_drive_migration_plan]]).
- Confirm Mac's dashboard, when pointed at Linux's API, renders live Linux data (not a stale/cached local copy).

## Status log (for whoever picks this up next — Codex, another Claude session, or the founder)

**Done, verified, as of 2026-09-06 ~20:20 IST:**
- Both machines enrolled in one Tailscale tailnet: Mac `100.117.111.80`, Linux (`gvc-ops-ai`) `100.86.74.97`. Confirmed reachable both directions.
- SSH bridge live: dedicated keypair `~/.ssh/shakthi_bridge_ed25519` on the Mac, public key in `blackboxops@100.86.74.97`'s `~/.ssh/authorized_keys`. OpenSSH server installed and running on Linux (it wasn't before).
- **Resolved a real naming confusion**: `~/ShakthiOS_v3.2` on Linux was the true 3.2 work (confirmed via its own `VERSION.txt` — "Revenue Mission Engine... Linux import based on the portable v3.1.1 snapshot taken 2026-09-03 from /Users/apple/shakthi-os"), sitting as 317 uncommitted files. `~/shakthi_os` (lowercase) on Linux is a separate, unrelated 2-commit project ("Commander v0") — not part of this line of work, left untouched.
- Backed up before touching anything (all still on disk): Linux `~/backups/ShakthiOS_v3.2_pre_upgrade_20260906_201333.tar.gz` (422MB), Linux `~/backups/shakthi_os_pre_upgrade_20260906_201333.tar.gz` (162MB), Mac `~/shakthi_os_backups/mac_shakthi-os_pre_upgrade_20260906_201333.tar.gz` (3.5MB).
- Committed Linux's 317-file WIP as a real commit (`39e2127`), merged into Mac's `main` (`64028d8`) — two trivial conflicts resolved (`SmartCopyButton.tsx` was byte-identical both sides; `orchestrator/api.py` import line was a strict superset on Linux's side). **Both machines are now at identical git history (`64028d8`)** — pushed Mac's merge to a side branch on Linux (`mac-3.2-merged`) since Linux's `main` was checked out, then fast-forwarded Linux's own `main` to it locally over SSH.
- Verified for real, not just claimed: 449/449 tests pass, `tsc --noEmit` clean, dashboard + API restarted and confirmed live on Mac (`/api/health` → `db_ok: true`; `/`, `/initiatives`, `/voice` all HTTP 200).
- Mac's own local `state/v3_1/*.db` runtime files were moved (not deleted) to `state/v3_1_mac_local_pre_merge_backup/` before the merge, since Linux's commit carried its own versions of those same paths.

**NOT done yet — this is the actual remaining scope of the spec:**
1. Mac still runs its own local `orchestrator/api.py` + dashboard (started during earlier troubleshooting, then again after the merge) — it has NOT been repointed to Linux's API yet. Mac is currently still a fully independent instance with its own `shakthi.db`, just now on the same *code* version as Linux, not the same *data*.
2. The founder's zero-drift requirement (Goal 7) is therefore not yet met — Mac and Linux still have two separate databases that can disagree.
3. Founder's latest instruction (2026-09-06 ~20:15 IST): **Mac = "commander"**, **Linux = "cloud PC"** — a change from the earlier confirmed answer ("Linux is control-plane, Mac contributes"). Current working interpretation (stated to the founder, not yet explicitly re-confirmed): Linux keeps holding the one real database and keeps doing the heavy execution — that's what a "cloud PC" is — while Mac becomes the lightweight terminal/interface the founder issues commands from and views status on. **Get an explicit confirmation of this reading before wiring `API_BASE`**, since it determines which machine's `shakthi.db` becomes the one kept and which gets archived.
4. Once that's confirmed: point Mac's `API_BASE` at Linux's tailnet address (`http://100.86.74.97:8787`), archive Mac's local `shakthi.db`, stop Mac's local API/dashboard processes, add the `executor=mac` polling endpoint to `orchestrator/api.py` on Linux, and run the round-trip validation (Task 12 status check from Mac, matching Linux exactly) described earlier in this spec.
5. The `linux-3.2` git remote is configured only on the Mac side (`blackboxops@100.86.74.97:ShakthiOS_v3.2`, via `GIT_SSH_COMMAND="ssh -i ~/.ssh/shakthi_bridge_ed25519"` since no SSH config alias exists yet) — future syncs should use this same path.

## Rollback

Every step is reversible: remove the git remote, delete `shakthi_bridge_ed25519` from Mac and its entry from Linux's `authorized_keys`, un-enroll either machine from Tailscale, restore Mac's archived `shakthi.db` and repoint `API_BASE` back to `127.0.0.1:8787` to return Mac to a fully standalone instance.
