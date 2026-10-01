# Mission Control runtime evidence — 2026-09-26

- Built dashboard artifact: successful Webpack production build.
- Started the existing orchestrator API on `127.0.0.1:8787`.
- Started the production dashboard on `127.0.0.1:3001`.
- API health: HTTP 200.
- `/mission-control`: HTTP 200, 16,398 bytes, 0.217 seconds.
- Rendered markers included `Living System View` and `Mission Control`.
- Both processes were stopped after the bounded smoke test; no listeners remain.

This proves the route renders with the current real API data path. It does not
prove that Paperclip or Hindsight agents are connected; their service probes
remain separate and honest.

After the support-service channel was added, a second production smoke test
returned HTTP 200 in 0.196 seconds with 16,995 bytes. The rendered HTML showed
separate `paperclip · not configured` and `hindsight · not configured` badges.
Mission Control's explicit refresh interval is now 30 seconds, preventing the
previous one-second request storm.
