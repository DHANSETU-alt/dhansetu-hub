# Scheduler audit — 2026-09-26

## Evidence

`crontab -l` shows multiple active scheduled paths for website review,
security scans and alerts, Sentinel checks and alerts, customer health,
watchdog scans and alerts, DNS checks, founder review, and live website watch.

This contradicts the mission requirement for one canonical scheduler. The
existing jobs are preserved as user-owned configuration; none were removed or
edited during this audit.

## Security finding

Several existing alert jobs contain a Telegram bot credential inline in the
crontab command. The value is intentionally omitted from this record and was
not copied into code, logs, or documentation. Treat the credential as exposed:

1. Rotate the Telegram bot token through the Telegram owner/admin flow.
2. Replace inline credentials with a protected environment/config mechanism.
3. Reconcile the jobs into one DhanSetu launchd scheduler only after backup,
   SSD availability, and founder approval of notification behavior.

No message was sent and no crontab mutation was performed by this audit.
