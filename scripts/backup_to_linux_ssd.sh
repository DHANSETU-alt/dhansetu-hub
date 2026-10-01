#!/bin/bash
# Real daily backup: pushes both real Shakthi_OS datasets (this Mac's, and
# Linux's own independent ShakthiOS_v3.2) onto the external SSD mounted on
# the Linux node -- so both real, live databases are protected before any
# future Linux OS wipe, and so the Mac's own real work has an off-machine
# copy. Authority stays on the Mac: this script runs FROM the Mac, pushing
# out over the already-verified SSH key, never the other way around.
#
# Real precondition: /mnt/backup_ssd must be mounted on the Linux side
# first (sudo mkdir -p /mnt/backup_ssd && sudo mount /dev/sda1 /mnt/backup_ssd)
# -- this script checks that honestly rather than assuming it.
set -euo pipefail

LINUX_HOST="blackboxops@192.168.31.27"
SSH_KEY="$HOME/.ssh/shakthi_bridge_ed25519"
SSH_OPTS=(-i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=5)
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_ROOT="/mnt/backup_ssd/shakthi_backups"

echo "== Checking backup SSD is actually mounted (not assuming) =="
if ! ssh "${SSH_OPTS[@]}" "$LINUX_HOST" "mountpoint -q /mnt/backup_ssd"; then
  echo "ERROR: /mnt/backup_ssd is not mounted on $LINUX_HOST. Run on Linux first:"
  echo "  sudo mkdir -p /mnt/backup_ssd && sudo mount /dev/sda1 /mnt/backup_ssd"
  exit 1
fi

ssh "${SSH_OPTS[@]}" "$LINUX_HOST" "mkdir -p '$BACKUP_ROOT/mac_shakthi_os/$TIMESTAMP' '$BACKUP_ROOT/linux_shakthios_v3.2/$TIMESTAMP'"

echo "== Backing up this Mac's real shakthi-os (code + shakthi.db) =="
rsync -az --delete \
  --exclude 'node_modules' --exclude '.next' --exclude 'dashboard/.next' \
  -e "ssh -i $SSH_KEY -o BatchMode=yes" \
  /Users/apple/shakthi-os/ \
  "$LINUX_HOST:$BACKUP_ROOT/mac_shakthi_os/$TIMESTAMP/"

echo "== Backing up Linux's own real, independent ShakthiOS_v3.2 (its live shakthi.db, this morning's work) =="
ssh "${SSH_OPTS[@]}" "$LINUX_HOST" \
  "rsync -a --delete --exclude 'node_modules' --exclude '.next' /home/blackboxops/ShakthiOS_v3.2/ '$BACKUP_ROOT/linux_shakthios_v3.2/$TIMESTAMP/'"

echo "== Real result =="
ssh "${SSH_OPTS[@]}" "$LINUX_HOST" "du -sh '$BACKUP_ROOT/mac_shakthi_os/$TIMESTAMP' '$BACKUP_ROOT/linux_shakthios_v3.2/$TIMESTAMP'; df -h /mnt/backup_ssd"
echo "Backup complete: $TIMESTAMP"
