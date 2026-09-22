# DhanSetu self-hosted runbook

The application remains on Supabase/Postgres until an explicit, tested database migration is completed. The Linux host runs the Next.js application; the external SSD stores durable application data, uploaded documents, backups, and logs. The SSD is not a server.

## One-time SSD setup

1. Identify the external device with `lsblk -f`; the verified current device is Kingston `/dev/sda1`, ext4, UUID `9e8acd1d-2da8-4593-9a90-3b3cd1af3968`. Do not create a filesystem on it.
2. After confirming that identity, copy the matching line from `ops/dhansetu-fstab.example` into `/etc/fstab` and mount it at `/mnt/dhansetu-data` with `nofail,x-systemd.device-timeout=10s` only if the service is configured to remain stopped when absent.
3. Set `DHANSETU_STORAGE_ROOT=/mnt/dhansetu-data` and `DHANSETU_STORAGE_UUID=<recorded UUID>` in a root-readable service environment, never in Git.
4. Run `scripts/storage-guard.sh`; it must return exit 0 before starting the app.

## Safe operations

```bash
scripts/storage-guard.sh
npm run build
scripts/backup-local.sh
npm run start
```

For a boot-managed deployment, install `ops/dhansetu-selfhost.service` as
`/etc/systemd/system/dhansetu-selfhost.service`, place non-Git secrets in
`/etc/dhansetu/dhansetu.env`, and enable it only after the SSD is mounted:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dhansetu-selfhost.service
systemctl status dhansetu-selfhost.service
```

The unit requires the SSD mount and runs the storage guard before the
standalone Next server. If the mount disappears, the service cannot write to
the empty mount path and must be stopped for recovery.

`scripts/backup-local.sh` stores a repository archive, a durable-data archive
(`app-data`, `postgres`, `documents`, and `logs`), checksums, and a metadata
inventory under the SSD backup directory. It excludes the backup directory
from the data archive and never copies service secrets. `ops/restore-test.sh`
verifies both archives in a temporary directory without overwriting live data.

If the SSD is missing, the guard exits 78 and the service must not start. Reconnect and mount the SSD, run the guard, then restore or start the service. Verify the archive checksum before restoring. Database restore is a separately reviewed operation; no production database is overwritten by this runbook.

## Traffic cutover

Keep the current Render/Cloudflare route serving until the local stack passes health, auth, payment webhook, upload authorization, backup/restore, and mobile smoke tests. Put a reverse proxy with TLS in front of the local app. Switch only the DNS origin/routing record needed for `dhansetuhub.in`, retain DNS security if desired, and keep the previous route for the rollback window.
