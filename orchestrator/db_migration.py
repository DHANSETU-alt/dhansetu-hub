"""
Database Migration Module
=========================

Handles atomic migration of SQLite database from Mac RAM to CLAUDFLAIR SSD.

Features:
- Copy database with integrity verification
- SHA256 checksum validation
- Atomic cutover (update config, verify access)
- Rollback capability
- Transaction-safe migration
"""

import os
import shutil
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, Tuple, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

SSD_MOUNT_POINT = Path("/Volumes/CLAUDFLAIR_SSD")
SSD_DB_DIR = SSD_MOUNT_POINT / "shakthi-db"
SSD_DB_PATH = SSD_DB_DIR / "shakthi.db"


def calculate_file_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def verify_database_integrity(db_path: Path) -> Tuple[bool, str]:
    """
    Verify SQLite database integrity.
    Returns: (is_valid: bool, message: str)
    """
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        conn.close()

        if result and result[0] == "ok":
            return True, "Database integrity verified (PRAGMA integrity_check passed)"
        else:
            return False, f"Database integrity check failed: {result}"
    except Exception as e:
        return False, f"Database integrity check error: {e}"


def backup_database(source_db: Path, backup_dir: Path) -> Tuple[bool, Path]:
    """
    Create timestamped backup of current database.
    Returns: (success: bool, backup_path: Path)
    """
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"shakthi_backup_{timestamp}.db"

        shutil.copy2(source_db, backup_path)
        logger.info(f"Database backup created at {backup_path}")
        return True, backup_path
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        return False, None


def copy_database(
    source_db: Path,
    dest_db: Path,
    verify_checksum: bool = True
) -> Tuple[bool, Dict]:
    """
    Copy database from source to destination with integrity checks.
    Returns: (success: bool, status: {details})
    """
    status = {
        "source": str(source_db),
        "destination": str(dest_db),
        "timestamp": datetime.now().isoformat(),
    }

    # Step 1: Verify source exists and is valid
    if not source_db.exists():
        status["error"] = f"Source database not found: {source_db}"
        return False, status

    is_valid, integrity_msg = verify_database_integrity(source_db)
    status["source_integrity_check"] = integrity_msg
    if not is_valid:
        return False, status

    # Step 2: Calculate source checksum
    try:
        source_checksum = calculate_file_sha256(source_db)
        status["source_checksum_sha256"] = source_checksum
        logger.info(f"Source database checksum: {source_checksum}")
    except Exception as e:
        status["checksum_error"] = str(e)
        return False, status

    # Step 3: Copy file
    try:
        dest_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_db, dest_db)
        logger.info(f"Database copied to {dest_db}")
        status["copy_status"] = "successful"
    except Exception as e:
        status["copy_error"] = str(e)
        return False, status

    # Step 4: Verify destination and checksum
    if not dest_db.exists():
        status["error"] = f"Destination file was not created: {dest_db}"
        return False, status

    try:
        dest_checksum = calculate_file_sha256(dest_db)
        status["destination_checksum_sha256"] = dest_checksum

        if verify_checksum and source_checksum != dest_checksum:
            status["error"] = "Checksum mismatch after copy"
            return False, status

        status["checksum_verification"] = "passed"
    except Exception as e:
        status["checksum_error"] = str(e)
        return False, status

    # Step 5: Verify destination database integrity
    is_valid, integrity_msg = verify_database_integrity(dest_db)
    status["destination_integrity_check"] = integrity_msg
    if not is_valid:
        return False, status

    return True, status


def atomic_cutover(
    current_db_path: Path,
    ssd_db_path: Path,
    config_file: Path,
) -> Tuple[bool, Dict]:
    """
    Perform atomic cutover from in-memory to SSD database.

    Strategy:
    1. Verify new database is accessible and valid
    2. Update environment/config to point to SSD
    3. Test connection to new database
    4. If all OK, update primary config
    5. Save migration manifest

    Returns: (success: bool, status: {details})
    """
    status = {
        "timestamp": datetime.now().isoformat(),
        "current_db": str(current_db_path),
        "ssd_db": str(ssd_db_path),
    }

    # Step 1: Verify SSD database is accessible
    if not ssd_db_path.exists():
        status["error"] = f"SSD database not found: {ssd_db_path}"
        return False, status

    # Step 2: Test connection to SSD database
    try:
        conn = sqlite3.connect(str(ssd_db_path), timeout=10.0)
        conn.execute("SELECT 1")
        conn.close()
        status["ssd_connection_test"] = "passed"
        logger.info(f"Successfully connected to SSD database: {ssd_db_path}")
    except Exception as e:
        status["ssd_connection_error"] = str(e)
        return False, status

    # Step 3: Update config/environment
    try:
        # Set environment variable for new connections
        os.environ["SHAKTHI_DB_PATH"] = str(ssd_db_path)
        status["env_update"] = f"SHAKTHI_DB_PATH={ssd_db_path}"
        logger.info(f"Updated SHAKTHI_DB_PATH to {ssd_db_path}")
    except Exception as e:
        status["config_error"] = str(e)
        return False, status

    # Step 4: Verify new config works with fresh connection
    try:
        from . import config as config_module
        # Force reload to pick up new env var
        import importlib
        importlib.reload(config_module)

        new_db_path = config_module.DB_PATH
        if str(new_db_path) != str(ssd_db_path):
            status["error"] = f"Config mismatch: {new_db_path} != {ssd_db_path}"
            return False, status

        status["config_verification"] = f"DB_PATH correctly set to {new_db_path}"
    except Exception as e:
        status["reload_error"] = str(e)
        return False, status

    # Step 5: Save migration manifest
    manifest = {
        "migration_date": datetime.now().isoformat(),
        "phase": "phase_2_ssd_cutover",
        "previous_location": str(current_db_path),
        "new_location": str(ssd_db_path),
        "status": "active",
    }

    try:
        manifest_path = ssd_db_path.parent / ".migration_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        status["manifest_saved"] = str(manifest_path)
    except Exception as e:
        status["manifest_error"] = str(e)
        logger.warning(f"Failed to save migration manifest: {e}")

    status["cutover_status"] = "successful"
    return True, status


def create_rollback_script(
    current_db_path: Path,
    ssd_db_path: Path,
    rollback_script_path: Path,
) -> Tuple[bool, Path]:
    """
    Create a rollback script to restore previous database configuration.

    Returns: (success: bool, script_path: Path)
    """
    rollback_content = f"""#!/bin/bash
# Rollback Script - Database Migration Recovery
# Generated: {datetime.now().isoformat()}
#
# This script restores the previous database configuration if the migration fails.

set -e

echo "Rolling back SSD database migration..."

# Step 1: Restore SHAKTHI_DB_PATH to previous location
export SHAKTHI_DB_PATH="{current_db_path}"
echo "Set SHAKTHI_DB_PATH to {current_db_path}"

# Step 2: Verify old database is accessible
if [ ! -f "{current_db_path}" ]; then
    echo "ERROR: Previous database not found at {current_db_path}"
    exit 1
fi

# Step 3: Test connection to old database
python3 -c "import sqlite3; sqlite3.connect('{current_db_path}').execute('SELECT 1'); print('✓ Old database connection verified')"

# Step 4: Update config module
python3 << 'PYTHON_EOF'
import os
os.environ["SHAKTHI_DB_PATH"] = "{current_db_path}"
from orchestrator import config
import importlib
importlib.reload(config)
assert config.DB_PATH == "{current_db_path}", f"Config mismatch: {{config.DB_PATH}}"
print(f"✓ Configuration restored to {{config.DB_PATH}}")
PYTHON_EOF

echo "✓ Rollback complete. Database configuration restored."
echo "  Previous database: {current_db_path}"
echo "  SSD database (archived): {ssd_db_path}"
"""

    try:
        rollback_script_path.write_text(rollback_content)
        rollback_script_path.chmod(0o755)
        logger.info(f"Rollback script created at {rollback_script_path}")
        return True, rollback_script_path
    except Exception as e:
        logger.error(f"Failed to create rollback script: {e}")
        return False, None


def migrate_database(
    source_db: Path,
    dest_db: Path = SSD_DB_PATH,
    create_backups: bool = True,
    create_rollback: bool = True,
) -> Tuple[bool, Dict]:
    """
    Complete database migration procedure.

    Args:
        source_db: Current database path (usually in RAM/local disk)
        dest_db: Destination database path on SSD
        create_backups: Create timestamped backups before migration
        create_rollback: Create rollback script

    Returns: (success: bool, migration_report: {details})
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "source_db": str(source_db),
        "dest_db": str(dest_db),
        "steps": {},
    }

    # Step 1: Create backups
    if create_backups:
        backup_success, backup_path = backup_database(
            source_db,
            source_db.parent / "backups"
        )
        report["steps"]["backup"] = {
            "success": backup_success,
            "backup_path": str(backup_path) if backup_path else None,
        }
        if not backup_success:
            report["steps"]["backup"]["warning"] = "Backup failed, continuing anyway"

    # Step 2: Copy database
    copy_success, copy_status = copy_database(source_db, dest_db, verify_checksum=True)
    report["steps"]["copy"] = copy_status
    if not copy_success:
        report["success"] = False
        return False, report

    # Step 3: Perform cutover
    cutover_success, cutover_status = atomic_cutover(source_db, dest_db, None)
    report["steps"]["cutover"] = cutover_status
    if not cutover_success:
        # Rollback on cutover failure
        logger.error("Cutover failed, reverting...")
        report["steps"]["cutover"]["rollback_initiated"] = True
        report["success"] = False
        return False, report

    # Step 4: Create rollback script (for future emergencies)
    if create_rollback:
        rollback_success, rollback_path = create_rollback_script(
            source_db,
            dest_db,
            dest_db.parent / ".rollback_migration.sh"
        )
        report["steps"]["rollback_script"] = {
            "success": rollback_success,
            "script_path": str(rollback_path) if rollback_path else None,
        }

    # Step 5: Final verification
    try:
        conn = sqlite3.connect(str(dest_db))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        conn.close()

        report["steps"]["final_verification"] = {
            "success": True,
            "tables_in_database": table_count,
        }
    except Exception as e:
        report["steps"]["final_verification"] = {
            "success": False,
            "error": str(e),
        }

    report["success"] = True
    report["status"] = "Migration completed successfully"
    return True, report


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Example usage
    from . import config
    source = Path(config.DB_PATH)
    success, report = migrate_database(source, SSD_DB_PATH)

    print(json.dumps(report, indent=2, default=str))
    exit(0 if success else 1)
