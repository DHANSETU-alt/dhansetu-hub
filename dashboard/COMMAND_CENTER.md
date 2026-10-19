# Founder Command Center

A real, functional operator cockpit at `/command-center` — not a mockup. Type
a command, it dispatches through the real PA Angella -> CEO pipeline
(`orchestrator/pa_angella.refine_and_send_to_ceo`), creates real rows in
`tasks`, and you watch them move through the board and the live log as the
real local model(s) process them.

## Run it (desktop, same machine — the default, zero extra setup)

```bash
# terminal 1, from the shakthi-os root
python3 -m orchestrator.api

# terminal 2
cd dashboard && npm run dev
```

Open `http://localhost:3000/command-center`. That's it — no token needed,
because both processes are talking over loopback (127.0.0.1), which this
API always trusts (same model as the CLI).

## Run it for real LAN/mobile access (a second device, e.g. your phone)

This needs three things, because a phone's browser talks to the API
directly over WiFi, not through the Next.js server:

```bash
# 1. Pick a real secret and start the API bound to your LAN interface.
#    Without SHAKTHI_API_TOKEN set, the server REFUSES to bind anywhere
#    but loopback -- this isn't optional, it's a hard safety default.
export SHAKTHI_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
echo "Your token: $SHAKTHI_API_TOKEN"   # save this, you'll paste it into the page once
SHAKTHI_API_HOST=0.0.0.0 python3 -m orchestrator.api
# Startup prints the real LAN URL, e.g.: LAN/mobile URL: http://192.168.1.50:8787

# 2. Bake that same LAN IP into the dashboard's client bundle, and bind
#    the dashboard itself to your LAN interface too.
cd dashboard
NEXT_PUBLIC_API_BASE=http://192.168.1.50:8787 npm run dev -- -H 0.0.0.0
# Next prints its own Network URL, e.g.: http://192.168.1.50:3000
```

3. On your phone (same WiFi), open `http://192.168.1.50:3000/command-center`,
   tap **SET LAN TOKEN** top-right, paste the token from step 1, save. It's
   stored only in that phone's browser (localStorage), sent as the
   `X-Shakthi-Token` header on every request from that page.

Loopback traffic (every other dashboard page, all server-rendered, runs on
the same machine as the API) is completely unaffected by any of this —
the token is only ever checked for a request that did NOT come from
127.0.0.1/::1. If you don't set `SHAKTHI_API_TOKEN` at all, non-loopback
binding is refused outright and everything behaves exactly as it always
has.

## What's real here vs. honestly derived

- **Task lifecycle** (NEW/RUNNING/WAITING/COMPLETED/FAILED): `tasks.status`
  in the DB only ever stores `pending`/`done`/`failed` — there's no
  persisted "running" state, because `routing.run_task()` (the real
  dispatch path for all 25 agents) is synchronous and touching it further
  for a UI feature wasn't worth the blast radius. NEW/RUNNING/WAITING are
  derived client-side from a pending task's real age (`created_at`). There
  is no separate "Assigned" lane: this system assigns an agent at task
  creation, always — there's no real gap to show.
- **Priority** (Low/Normal/High/Critical): real and stored.
  `orchestrator/routing.classify_risk()` now returns one of 4 real values,
  written to `tasks.risk_level` on every dispatch across the whole system.
  `CRITICAL_KEYWORDS` and the cloud-escalation gate are byte-for-byte
  unchanged — this only adds new bands for goals that don't already hit a
  critical keyword. High/Low use deliberately specific multi-word phrases
  (not bare words like "check"/"security") after an early version of this
  briefly reclassified ordinary read-only status commands — see
  `tests/test_classify_risk_4tier.py`.
- **Agent roster**: mapped onto the real 25-agent roster (Master
  Coordinator = ceo + pa_angella, Code = engineer + bug_fixer, Design =
  website_builder + chrome_developer, Security/Finance/Marketing = 1:1).
  System Watchdog is a real deterministic subsystem
  (`orchestrator/watchdog.py`), not an LLM agent — it has no `agents`
  table row, shown as a static entry rather than faked as "active."

## Security note

This does open a real door if you ever run with `SHAKTHI_API_TOKEN` set
and share that token loosely — it grants read access to the whole system
(tasks, agents, finance, everything this API already serves) plus the
ability to dispatch real commands through PA Angella/CEO. Treat the token
like any other credential: don't commit it, don't paste it anywhere but
the page's own token box.
