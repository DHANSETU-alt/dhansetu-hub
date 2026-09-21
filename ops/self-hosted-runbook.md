# DhanSetu self-hosted runbook

The application remains on Supabase/Postgres until an explicit, tested database migration is completed. The Linux host runs the Next.js application; the external SSD stores durable application data, uploaded documents, backups, and logs. The SSD is not a server.

## One-time SSD setup

1. Identify the external device with `lsblk -f` and create a filesystem only after confirming the exact device.
2. Record its UUID in `/etc/fstab` and mount it at `/mnt/dhansetu-data` with `nofail,x-systemd.device-timeout=10s` only if the service is configured to remain stopped when absent.
3. Set `DHANSETU_STORAGE_ROOT=/mnt/dhansetu-data` and `DHANSETU_STORAGE_UUID=<recorded UUID>` in a root-readable service environment, never in Git.
4. Run `scripts/storage-guard.sh`; it must return exit 0 before starting the app.

## Safe operations

```bash
scripts/storage-guard.sh
npm run build
scripts/backup-local.sh
npm run start
```

If the SSD is missing, the guard exits 78 and the service must not start. Reconnect and mount the SSD, run the guard, then restore or start the service. Verify the archive checksum before restoring. Database restore is a separately reviewed operation; no production database is overwritten by this runbook.

## Traffic cutover

Keep the current Render/Cloudflare route serving until the local stack passes health, auth, payment webhook, upload authorization, backup/restore, and mobile smoke tests. Put a reverse proxy with TLS in front of the local app. Switch only the DNS origin/routing record needed for `dhansetuhub.in`, retain DNS security if desired, and keep the previous route for the rollback window.
