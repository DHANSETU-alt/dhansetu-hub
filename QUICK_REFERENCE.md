# Phase 2 SSD Migration - Quick Reference

## Pre-Migration (5 minutes)

```bash
# 1. Verify SSD connection
diskutil list | grep CLAUDFLAIR
df -h /Volumes/CLAUDFLAIR_SSD

# 2. Backup current database
cp $SHAKTHI_DB_PATH backups/pre_migration_$(date +%s).db

# 3. Verify current database health
python3 << 'EOF'
import sqlite3
from pathlib import Path
from orchestrator import config

conn = sqlite3.connect(config.DB_PATH)
cursor = conn.cursor()
cursor.execute("PRAGMA integrity_check")
print(f"✓ Database OK" if cursor.fetchone()[0] == "ok" else "✗ Database corrupt")
conn.close()
EOF
```

## Migration (3 steps, ~20 minutes)

```bash
# Step 1: Initialize SSD directories
python3 << 'EOF'
from orchestrator.ssd_migration import setup_ssd
success, status = setup_ssd()
print("✓ SSD initialized" if success else "✗ Failed")
EOF

# Step 2: Migrate database
python3 << 'EOF'
from orchestrator.db_migration import migrate_database
from orchestrator.config import DB_PATH
from pathlib import Path

success, report = migrate_database(Path(DB_PATH))
print("✓ Database migrated" if success else "✗ Migration failed")
EOF

# Step 3: Run startup sequence
export SHAKTHI_DB_PATH="/Volumes/CLAUDFLAIR_SSD/shakthi-db/shakthi.db"
./orchestrator/startup.sh
```

## Verification (5 minutes)

```bash
# Test database
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect("/Volumes/CLAUDFLAIR_SSD/shakthi-db/shakthi.db")
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
tables = cursor.fetchone()[0]
conn.close()
print(f"✓ Database ready ({tables} tables)")
EOF

# Test API
curl http://localhost:8000/health

# Check disk space
df -h /Volumes/CLAUDFLAIR_SSD
```

## Quick Rollback

```bash
# Automatic
./orchestrator/startup.sh --rollback

# Manual
bash /Volumes/CLAUDFLAIR_SSD/shakthi-db/.rollback_migration.sh
```

## Monitoring

```bash
# View SSD health
python3 << 'EOF'
from orchestrator.ssd_health import get_ssd_monitor
import json
status = get_ssd_monitor().get_health_status()
print(json.dumps(status, indent=2, default=str))
EOF

# View cache stats
python3 << 'EOF'
from orchestrator.session_cache_migration import get_session_manager
stats = get_session_manager().get_cache_stats()
print(f"Sessions: {stats['sessions_count']}")
print(f"Cache entries: {stats['cache_entries_count']}")
print(f"Cache hits: {stats['total_cache_hits']}")
EOF

# Watch disk
watch -n 5 'df -h /Volumes/CLAUDFLAIR_SSD'
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| SSD not mounted | `diskutil mount /Volumes/CLAUDFLAIR_SSD` |
| Database not found | Re-run migration step 2 |
| High latency (>100ms) | Check disk space: `df -h /Volumes/CLAUDFLAIR_SSD` |
| Checksum mismatch | Run migration again |
| API won't start | `echo $SHAKTHI_DB_PATH` (should be SSD path) |
| Sessions lost | Cache DB may have expired entries (check logs) |

## Files to Review

- **Setup Guide**: `SSD_MIGRATION_GUIDE.md`
- **Implementation**: `SSD_MIGRATION_README.md`
- **Delivery**: `PHASE2_DELIVERY_SUMMARY.md`
- **Tests**: `orchestrator/test_ssd_migration.py`

## Key Paths

```
Database:        /Volumes/CLAUDFLAIR_SSD/shakthi-db/shakthi.db
Session Cache:   /Volumes/CLAUDFLAIR_SSD/cache/session_cache.db
Logs:            /Volumes/CLAUDFLAIR_SSD/logs/
Backups:         /Volumes/CLAUDFLAIR_SSD/backups/
Rollback Script: /Volumes/CLAUDFLAIR_SSD/shakthi-db/.rollback_migration.sh
Health Log:      /Volumes/CLAUDFLAIR_SSD/logs/ssd_health.log
```

## Environment Variables

```bash
export SHAKTHI_DB_PATH="/Volumes/CLAUDFLAIR_SSD/shakthi-db/shakthi.db"
export SHAKTHI_LOGS_PATH="/Volumes/CLAUDFLAIR_SSD/logs"
export SHAKTHI_CACHE_PATH="/Volumes/CLAUDFLAIR_SSD/cache"
```

## Testing

```bash
# Run all tests
python3 -m orchestrator.test_ssd_migration

# Run specific test
python3 -m unittest orchestrator.test_ssd_migration.TestDatabaseMigration
```

## Performance Targets

| Metric | Target | How to Verify |
|--------|--------|---------------|
| Read latency | <20ms | health status report |
| Write latency | <30ms | health status report |
| Cache hit rate | >90% | cache stats |
| Disk free | >500MB | `df -h /Volumes/CLAUDFLAIR_SSD` |
| Tables preserved | 100% | row count verification |

---

**Time Estimate**: 30-45 minutes total  
**Risk Level**: Low (rollback available)  
**Recommendation**: Execute during maintenance window
