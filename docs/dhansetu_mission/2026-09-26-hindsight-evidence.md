# Hindsight integration evidence — 2026-09-26

- Checkout: `/Users/apple/shakthi-services/hindsight`
- Canonical-side adapter: `orchestrator/hindsight_gateway.py`
- Sentinel now exposes a `hindsight` service status.
- Sentinel also exposes a separate `paperclip` reachability status; this is
  deliberately not treated as proof that any agent is connected.
- Default behavior is explicit `not configured (set HINDSIGHT_API_URL)`.
- Configured but unreachable endpoints return `unavailable` after a bounded
  1.5-second request timeout.
- Successful `/health` responses return `reachable`.
- No API key, memory content, or secret is logged or returned.

Verification:

```text
python3 -m unittest tests.test_hindsight_gateway -v  -> 4 tests passed
python3 -m py_compile orchestrator/hindsight_gateway.py orchestrator/sentinel.py
service_status()['hindsight'] -> not configured (set HINDSIGHT_API_URL)
```

The actual Hindsight server remains unstarted because no LLM provider or local
model endpoint is configured. The checkout's supported bare-metal command is
`hindsight-api` (or `uv run` from the workspace), but it is intentionally not
launched until the SSD-backed database location and provider are explicitly
configured. Memory retain/recall is not claimed as live.
