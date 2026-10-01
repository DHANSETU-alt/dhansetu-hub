# DhanSetu launchd runbook

Prepared templates live in `launchd/` and are not installed while the SSD is
absent.

## Founder action after the SSD is mounted

Create `/Users/apple/.config/dhansetu/host.env` with the exact confirmed
volume path, for example:

```zsh
DHANSETU_SSD_ROOT=/Volumes/<confirmed-volume>/DhanSetu
```

Do not use the example literally. Confirm the volume with `diskutil list` and
`df -P` first; never point it at the internal disk.

## Installation sequence

After `scripts/dhansetu-host.sh check-storage` succeeds, copy the three plist
templates to `~/Library/LaunchAgents/` as `in.dhansetu.api.plist`,
`in.dhansetu.web.plist`, and `in.dhansetu.paperclip.plist`, then load them with
`launchctl bootstrap gui/$(id -u)`.
Verify with `launchctl print gui/$(id -u)/in.dhansetu.api` and the web label.

The API and web jobs use absolute paths, loopback services, KeepAlive, and a
30-second restart throttle. Missing `host.env` or an absent SSD causes the
wrapper to exit before application state can be written.

Use `scripts/dhansetu-health.sh` to check only the DhanSetu API and web ports.
Use `scripts/dhansetu-stop.sh` to unload only the three DhanSetu launchd labels.

## Current evidence

- All three plist templates pass `plutil -lint`.
- Shell syntax checks pass.
- With no `host.env`, the launch wrapper returned the expected safe refusal.
- With both services stopped, the health command returned `api: UNAVAILABLE
  (000)` and exited non-zero; it did not inspect or alter unrelated ports.
- No launchd job was installed or loaded.
