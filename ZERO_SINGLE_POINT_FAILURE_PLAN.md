# Zero Single-Point-of-Failure Plan

Forward-looking companion to `SYSTEM_HARDENING_REPORT.md`. That document proves today's architecture has no CEO single point of failure. This one states the actual invariant to protect, and the real conditions that would break it — so the next person (or agent) touching this code knows what not to do, instead of re-discovering it the hard way.

## The invariant, stated precisely

**No agent-level failure may prevent another module's core operation from completing.** Concretely, right now: `sentinel.collect_health()`, `security.security_posture_scan()`, `finance.generate_report()`, and `worker_pool.drain_queue()` must never import, call, or block on `ceo.decide()` (or any other single agent) to do their own job. This is verifiable with one command:

```bash
grep -n "ceo\." orchestrator/security.py orchestrator/sentinel.py orchestrator/finance.py
# must return nothing
```
`governor.check_subsystems()` re-checks the *behavioral* version of this same invariant on every call — not just that the import graph is clean, but that each subsystem actually runs.

## What would actually break this invariant (the real risk list)

1. **A future feature adds a CEO-approval gate to one of the four core subsystems above**, the way Correction Bot / Chrome Developer / Website Builder already do. That's fine *only if* it's wrapped in the same try/except-and-fall-back-safely pattern those three already use. The risk is someone adding a bare, unguarded `ceo.decide()` call inside `sentinel.py` or `finance.py` itself — that would be new, real coupling, not present today.
2. **A gate that fails closed to something unsafe instead of something conservative.** Every existing CEO gate defaults to "not approved" on failure. A new one that defaulted to "approved" on failure would be worse than no gate at all — silent, wrong approval is the one failure mode this whole codebase has been deliberately built to avoid (see `ceo.py`'s own comment: "a mis-parsed decision must not be mistaken for an approved one").
3. **Sharing a single SQLite connection across the boundary.** The real bug fixed in the CEO investigation (`_try_cloud` discarding local output) and the real bug fixed in the Worker Pool work (SQLite lock contention across threads) were both connection-handling bugs, not architecture bugs. The next one will look the same: some function holding a `with db.get_conn()` block open across a slow call (a model call, a subprocess, a network request) that another concurrent path also needs to write through. Rule that prevents it, already followed everywhere in this codebase: never call a slow operation while a database transaction is open; open a fresh connection after it returns.
4. **A genuinely new external dependency becoming load-bearing for multiple modules without a fallback** — e.g., if Ollama itself becomes unreachable, *every* agent is affected, not just CEO, because every agent routes through the same `model_gateway.call_local()`. This is a real, already-existing shared dependency (correctly, since local models are the whole point of this system) — it's not a "CEO problem," it's a "the local model server is down" problem, and `sentinel.check_sentinel()`'s existing "Ollama is not reachable" alert already covers it. Worth naming here so it isn't mistaken for a CEO-specific gap later.

## What NOT to build in response to a future version of this same request

- A duplicate router/kernel alongside `routing.py` — confirmed today, again, that `routing.py` already dispatches every agent identically.
- A "policy cache" with no real policy concept behind it — would be product design dressed as hardening.
- An active supervisor process that restarts/retries CEO — the historical failures were a logic bug (fixed), not transient unavailability; a retry loop around a fixed bug adds complexity with nothing left to catch.

## What to build if the invariant is ever actually threatened

If risk #1 above happens (a new unguarded gate gets added somewhere it shouldn't), the fix is the same three-line pattern already used four times in this codebase: wrap the call, catch the exception, default to the conservative outcome, log it. Not a new subsystem — the existing pattern, applied.
