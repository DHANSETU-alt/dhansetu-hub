# SSD Migration & Hosting Cutover Guide

## Overview

**Phase 1 → Phase 2 Migration**: Seamless cutover from Mac in-memory storage (ICA) to CLAUDFLAIR external SSD for persistent, disk-backed storage.

- **Phase 1**: In-memory storage on Mac
- **Phase 2**: SSD-backed persistent storage on CLAUDFLAIR

This guide covers the complete migration procedure, verification steps, rollback procedures, and troubleshooting.

---

## Pre-Migration Checklist

Before starting migration, verify:

- [ ] CLAUDFLAIR external SSD is connected and recognized
- [ ] SSD has at least 10GB free space
- [ ] Current database is healthy (`PRAGMA integrity_check` passes)
- [ ] No active API requests or background tasks
- [ ] Recent backup of current database exists
- [ ] All logs from Phase 1 are reviewed
- [ ] Maintenance window is scheduled (recommend 15-30 minutes)

### Verify SSD Connection

```bash
# Check if SSD is mounted
diskutil list | grep CLAUDFLAIR

# Verify SSD mount point
ls -la /Volumes/CLAUDFLAIR_SSD

# Check free space
df -h /Volumes/CLAUDFLAIR_SSD
```

### Backup Current Database

```bash
# Create backup before migration
cp $SHAKTHI_DB_PATH backups/shakthi_pre_migration_$(date +%Y%m%d_%H%M%S).db
```

---

## Migration Procedure

### Step 1: Initialize SSD Directories

```bash
cd /Users/apple/shakthi-os

python3 << 'EOF'
from orchestrator.ssd_migration import setup_ssd
import json

success, status = setup_ssd()
print(json.dumps(status, indent=2))

if not success:
    print("❌ SSD setup failed")
    exit(1)
print("✓ SSD directories initialized")
EOF
```

**Expected output:**
```json
{
  "step": "complete_setup",
  "success": true,
  "directories": {
    "database": "initialized at /Volumes/CLAUDFLAIR_SSD/shakthi-db",
    "logs": "initialized at /Volumes/CLAUDFLAIR_SSD/logs",
    "cache": "initialized at /Volumes/CLAUDFLAIR_SSD/cache",
    "uploads": "initialized at /Volumes/CLAUDFLAIR_SSD/uploads",
    "backups": "initialized at /Volumes/CLAUDFLAIR_SSD/backups"
  },
  "message": "SSD setup successful"
}
```

### Step 2: Migrate Database

```bash
cd /Users/apple/shakthi-os

python3 << 'EOF'
from orchestrator.db_migration import migrate_database
from orchestrator.config import DB_PATH
from pathlib import Path
import json

# Perform migration
success, report = migrate_database(
    source_db=Path(DB_PATH),
    dest_db=Path("/Volumes/CLAUDFLAIR_SSD/shakthi-db/shakthi.db"),
    create_backups=True,
    create_rollback=True
)

print(json.dumps(report, indent=2))

if not success:
    print("❌ Database migration failed")
    exit(1)
print("✓ Database migration successful")
EOF
```

**Expected output:**
- Checksum verification passed
- Database integrity confirmed
- Rollback script created
- All data preserved

### Step 3: Run Startup Sequence

```bash
cd /Users/apple/shakthi-os

# Set environment variable for SSD database path
export SHAKTHI_DB_PATH="/Volumes/CLAUDFLAIR_SSD/shakthi-db/shakthi.db"

python3 << 'EOF'
from orchestrator.startup import run_startup
import json

success, report = run_startup()
print(json.dumps(report, indent=2))

if not success:
    print("❌ Startup failed")
    exit(1)
print("✓ Startup sequence successful")
EOF
```

**Expected output:**
- SSD mounted ✓
- Database accessible ✓
- Session/cache migrated ✓
- Health checks passed ✓
- Disk space adequate ✓

### Step 4: Verify Migration

```bash
# Check that database is on SSD
echo "Database location:"
echo $SHAKTHI_DB_PATH

# Verify database works
python3 << 'EOF'
import sqlite3

db_path = "/Volumes/CLAUDFLAIR_SSD/shakthi-db/shakthi.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Count tables
cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
table_count = cursor.fetchone()[0]

# Test write
cursor.execute("PRAGMA optimize")

conn.close()
print(f"✓ Database verified: {table_count} tables")
EOF

# Verify logs directory
ls -la /Volumes/CLAUDFLAIR_SSD/logs/

# Verify cache directory
ls -la /Volumes/CLAUDFLAIR_SSD/cache/

# Verify disk space
df -h /Volumes/CLAUDFLAIR_SSD/
```

### Step 5: Start Application Services

```bash
# Set environment for new connections
export SHAKTHI_DB_PATH="/Volumes/CLAUDFLAIR_SSD/shakthi-db/shakthi.db"

# Start API server (adjust command per your setup)
python3 -m orchestrator.api &

# Verify API is responding
sleep 5
curl http://localhost:8000/health

# Check that database queries work
python3 << 'EOF'
import requests
response = requests.get("http://localhost:8000/health")
if response.status_code == 200:
    print("✓ API responding")
else:
    print(f"❌ API returned {response.status_code}")
EOF
```

---

## Cutover Checklist

After migration completes:

- [ ] SSD directories created
- [ ] Database copied with checksum verification
- [ ] Startup sequence passed all health checks
- [ ] API server responds to requests
- [ ] Database read/write latency acceptable (<100ms)
- [ ] Disk space adequate (>500MB free)
- [ ] No errors in logs
- [ ] Rollback script created and tested

### Make Cutover Permanent

Update your shell configuration to always use SSD database:

```bash
# Add to ~/.zshrc or ~/.bash_profile
export SHAKTHI_DB_PATH="/Volumes/CLAUDFLAIR_SSD/shakthi-db/shakthi.db"
```

Or update application startup script to set this environment variable.

---

## Rollback Procedure

If migration encounters issues, rollback to the previous database:

### Automatic Rollback (Immediate)

A rollback script is created during migration at:
```
/Volumes/CLAUDFLAIR_SSD/shakthi-db/.rollback_migration.sh
```

To use it:

```bash
bash /Volumes/CLAUDFLAIR_SSD/shakthi-db/.rollback_migration.sh
```

This will:
1. Restore `SHAKTHI_DB_PATH` to previous location
2. Verify old database is accessible
3. Update application config
4. Restart services

### Manual Rollback

If automatic rollback fails:

```bash
# Step 1: Stop application services
pkill -f "python3 -m orchestrator"
sleep 5

# Step 2: Restore environment variable
export SHAKTHI_DB_PATH="/Users/apple/shakthi-os/shakthi.db"

# Step 3: Verify old database exists and is healthy
python3 << 'EOF'
import sqlite3
from pathlib import Path

old_db = Path("/Users/apple/shakthi-os/shakthi.db")
if old_db.exists():
    conn = sqlite3.connect(str(old_db))
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check")
    result = cursor.fetchone()
    conn.close()
    
    if result[0] == "ok":
        print("✓ Old database is healthy")
    else:
        print(f"❌ Old database integrity check failed: {result}")
else:
    print(f"❌ Old database not found at {old_db}")
EOF

# Step 4: Restart application services
# (adjust command per your setup)
python3 -m orchestrator.api &

# Step 5: Verify services are responding
sleep 5
curl http://localhost:8000/health
```

### Verify Rollback Success

```bash
# Check active database
echo "Current database: $SHAKTHI_DB_PATH"

# Verify database works
python3 << 'EOF'
import sqlite3
from pathlib import Path
from orchestrator import config

db_path = config.DB_PATH
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
count = cursor.fetchone()[0]
conn.close()
print(f"✓ Database at {db_path} has {count} tables")
EOF
```

### Archive SSD Database (Optional)

After confirming rollback was successful and your system is stable (24+ hours):

```bash
# Keep the SSD database as backup
cp /Volumes/CLAUDFLAIR_SSD/shakthi-db/shakthi.db \
   /Volumes/CLAUDFLAIR_SSD/backups/shakthi_migration_failed_$(date +%Y%m%d).db
```

---

## Monitoring & Maintenance

### Enable SSD Health Monitoring

```bash
python3 << 'EOF'
from orchestrator.ssd_health import setup_ssd_monitoring
import time

# Start monitoring
setup_ssd_monitoring(check_interval_seconds=60)

# Let it run for a bit
time.sleep(300)

print("✓ SSD health monitoring active")
print("Check logs at /Volumes/CLAUDFLAIR_SSD/logs/ssd_health.log")
EOF
```

### Health Check Commands

```bash
# View SSD health status
python3 << 'EOF'
from orchestrator.ssd_health import get_ssd_monitor
import json

monitor = get_ssd_monitor()
status = monitor.get_health_status()
print(json.dumps(status, indent=2, default=str))
EOF

# Monitor disk space
watch -n 5 'df -h /Volumes/CLAUDFLAIR_SSD'

# Monitor database latency
python3 << 'EOF'
import sqlite3
import time
from pathlib import Path
from orchestrator import config

db_path = Path(config.DB_PATH)
for i in range(5):
    start = time.time()
    conn = sqlite3.connect(str(db_path))
    conn.execute("SELECT 1")
    conn.close()
    latency = (time.time() - start) * 1000
    print(f"Read latency: {latency:.1f}ms")
    time.sleep(2)
EOF
```

### Session/Cache Statistics

```bash
python3 << 'EOF'
from orchestrator.session_cache_migration import get_session_manager
import json

manager = get_session_manager()
stats = manager.get_cache_stats()
print(json.dumps(stats, indent=2))
EOF
```

---

## Troubleshooting

### Problem: "SSD not mounted"

```bash
# Check mount status
diskutil list | grep CLAUDFLAIR

# If not mounted, mount manually
diskutil mount /Volumes/CLAUDFLAIR_SSD

# If mount fails, check if SSD is recognized
diskutil list
```

### Problem: "Database not found on SSD"

```bash
# Check if migration completed
ls -la /Volumes/CLAUDFLAIR_SSD/shakthi-db/

# If missing, re-run migration from step 2
# Or restore from backup if available
```

### Problem: "High database latency (>100ms)"

```bash
# Check SSD disk space
df -h /Volumes/CLAUDFLAIR_SSD/

# If space is low (<500MB), clean up old logs/backups
du -sh /Volumes/CLAUDFLAIR_SSD/logs/
du -sh /Volumes/CLAUDFLAIR_SSD/backups/

# Check if SSD is performing well
diskutil secureErase 0 /Volumes/CLAUDFLAIR_SSD  # WARNING: destructive!

# Or check with system tools
system_profiler SPUSBDataType | grep -i claudflair
```

### Problem: "Migration checksum mismatch"

```bash
# Verify source database integrity
python3 << 'EOF'
import sqlite3
from pathlib import Path
from orchestrator.config import DB_PATH

db_path = Path(DB_PATH)
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()
cursor.execute("PRAGMA integrity_check")
result = cursor.fetchone()
conn.close()

print(f"Source database integrity: {result[0]}")
EOF

# Re-run migration from step 2
```

### Problem: "API won't start after migration"

```bash
# Check if SHAKTHI_DB_PATH is set correctly
echo $SHAKTHI_DB_PATH

# Verify database file exists
ls -la /Volumes/CLAUDFLAIR_SSD/shakthi-db/shakthi.db

# Check application logs
tail -100 /Volumes/CLAUDFLAIR_SSD/logs/*.log

# Attempt rollback if issues persist
bash /Volumes/CLAUDFLAIR_SSD/shakthi-db/.rollback_migration.sh
```

### Problem: "Sessions lost after restart"

```bash
# Verify cache database exists
ls -la /Volumes/CLAUDFLAIR_SSD/cache/session_cache.db

# Check cache database integrity
python3 << 'EOF'
import sqlite3

db_path = "/Volumes/CLAUDFLAIR_SSD/cache/session_cache.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM sessions")
session_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM cache_entries")
cache_count = cursor.fetchone()[0]

conn.close()

print(f"Sessions: {session_count}")
print(f"Cache entries: {cache_count}")
EOF

# If cache is empty, sessions were cleared normally
# Re-login users or restore from backup
```

---

## Testing & Validation

### Run Full Test Suite

```bash
cd /Users/apple/shakthi-os
python3 -m orchestrator.test_ssd_migration

# Output should show:
# - 5000 record insert/verify test ✓
# - Session persistence test ✓
# - Cache hit rate >90% ✓
# - SSD failure recovery test ✓
```

### Performance Baseline

Before and after migration, measure performance:

```bash
python3 << 'EOF'
import sqlite3
import time
from pathlib import Path
from orchestrator import config

db_path = Path(config.DB_PATH)

# Measure read performance
reads = []
for _ in range(100):
    start = time.time()
    conn = sqlite3.connect(str(db_path))
    conn.execute("SELECT COUNT(*) FROM sqlite_master")
    conn.close()
    reads.append((time.time() - start) * 1000)

avg_read = sum(reads) / len(reads)
p99_read = sorted(reads)[int(len(reads) * 0.99)]

print(f"Read latency: avg={avg_read:.1f}ms, p99={p99_read:.1f}ms")

# Phase 1 baseline: typically 2-5ms (in-memory)
# Phase 2 target: <30ms on SSD
EOF
```

---

## Performance Expectations

### Latency Changes

| Operation | Phase 1 (RAM) | Phase 2 (SSD) | Notes |
|-----------|---------------|---------------|-------|
| Read      | 2-5ms         | 5-20ms        | Acceptable for most workloads |
| Write     | 2-5ms         | 10-30ms       | Database may batch writes |
| Session   | <1ms          | 5-15ms        | Fallback to memory if SSD fails |

### Disk Space Usage

| Component | Typical Size |
|-----------|--------------|
| Database  | 100-500MB    |
| Logs      | 10-50MB/day  |
| Cache     | 50-200MB     |
| Uploads   | Variable     |
| **Total** | **> 1GB**    |

Ensure SSD has **at least 10GB** free for normal operation.

---

## Support & Escalation

If you encounter issues:

1. **Check logs**: `/Volumes/CLAUDFLAIR_SSD/logs/`
2. **Review this guide**: Troubleshooting section
3. **Attempt rollback**: Last resort if critical issues occur
4. **Contact administrator** with:
   - Exact error message
   - Contents of startup report
   - SSD health status
   - Recent log entries

---

## Appendix: Manual Database Verification

```bash
# Complete database health check
python3 << 'EOF'
import sqlite3
from pathlib import Path
from orchestrator import config

db_path = Path(config.DB_PATH)

print(f"Database: {db_path}")
print(f"Exists: {db_path.exists()}")
print(f"Size: {db_path.stat().st_size / (1024*1024):.1f}MB")

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Integrity check
cursor.execute("PRAGMA integrity_check")
integrity = cursor.fetchone()[0]
print(f"Integrity: {integrity}")

# Table count
cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
tables = cursor.fetchone()[0]
print(f"Tables: {tables}")

# Journal mode
cursor.execute("PRAGMA journal_mode")
journal = cursor.fetchone()[0]
print(f"Journal mode: {journal}")

# Statistics
cursor.execute("SELECT SUM(pgcount) FROM dbstat")
page_count = cursor.fetchone()[0]
print(f"Pages: {page_count}")

conn.close()
EOF
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-10-01  
**Status**: Phase 2 SSD Migration Ready
