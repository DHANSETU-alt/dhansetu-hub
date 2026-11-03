# Render runtime compatibility fix

## Root cause measured 2026-11-03

Render build logs identify `NODE_VERSION=20.20.2` from a service environment variable. The locked dependency `better-sqlite3@13.0.3` declares `engines.node >=22`. In isolated temporary installs, loading this addon under Node 20.20.2 exited with signal 11; installing and querying SQLite under Node 24.22.2 succeeded. The public Render process repeatedly exits 139 shortly after Next reports ready, and the DhanSetu service currently returns 502/503.

This is a direct runtime compatibility reproduction and matches the observed native segfault. It is stronger than an OOM hypothesis: Render's sampled memory was about 54–73 MB against a 512 MiB limit.

## Source safeguard prepared

- `.node-version` pins 24.22.2 for hosts that read the repository file.
- `package.json` and the lockfile require Node `>=22 <27`, so incompatible installs fail early.

## Remaining live action

Render docs state that a dashboard `NODE_VERSION` environment variable overrides `.node-version`. The live service still has that variable set to 20.20.2. Set it to 24.22.2 (or remove it so the repository pin applies), then rebuild and verify `/api/health`, `/checkout`, and `/gst` over HTTPS. No Render environment or deployment was changed in this local step.
