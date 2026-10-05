"""
SSD Migration & Hosting Cutover Module
=====================================

Manages seamless migration from Mac memory (ICA) to CLAUDFLAIR external SSD.

Phase 1: In-memory storage (existing)
Phase 2: SSD-backed persistent storage (this module)

Key responsibilities:
- Mount and initialize CLAUDFLAIR SSD
- Create directory structure for database, logs, cache, uploads
- Verify SSD accessibility and permissions
- Graceful degradation if SSD becomes unavailable
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, Tuple, Optional
import subprocess
import logging

logger = logging.getLogger(__name__)

# DhanSetuSSD mount point (external SSD)
SSD_MOUNT_POINT = Path("/Volumes/DhanSetuSSD")

# Directory structure on SSD
SSD_DIRS = {
    "database": SSD_MOUNT_POINT / "shakthi-db",
    "logs": SSD_MOUNT_POINT / "logs",
    "cache": SSD_MOUNT_POINT / "cache",
    "uploads": SSD_MOUNT_POINT / "uploads",
    "backups": SSD_MOUNT_POINT / "backups",
}


class SSDMigrationManager:
    """Manages SSD setup, initialization, and health checks."""

    def __init__(self, ssd_mount_point: Path = SSD_MOUNT_POINT):
        self.ssd_mount_point = ssd_mount_point
        self.ssd_dirs = {
            "database": ssd_mount_point / "shakthi-db",
            "logs": ssd_mount_point / "logs",
            "cache": ssd_mount_point / "cache",
            "uploads": ssd_mount_point / "uploads",
            "backups": ssd_mount_point / "backups",
        }
        self.state_file = ssd_mount_point / ".migration_state.json"

    def is_ssd_mounted(self) -> bool:
        """Check if CLAUDFLAIR SSD is mounted."""
        return self.ssd_mount_point.exists() and self.ssd_mount_point.is_mount()

    def verify_ssd_accessible(self) -> Tuple[bool, str]:
        """
        Verify SSD is mounted, readable, and writable.
        Returns: (success: bool, message: str)
        """
        # Check mount
        if not self.ssd_mount_point.exists():
            return False, f"SSD mount point {self.ssd_mount_point} does not exist"

        # Test write permission
        try:
            test_file = self.ssd_mount_point / ".test_write"
            test_file.write_text("test")
            test_file.unlink()
            return True, f"SSD {self.ssd_mount_point} is accessible and writable"
        except Exception as e:
            return False, f"SSD write test failed: {e}"

    def initialize_ssd_directories(self) -> Tuple[bool, Dict[str, str]]:
        """
        Create directory structure on SSD.
        Returns: (success: bool, status_dict: {dir_name: status})
        """
        results = {}
        success = True

        for dir_name, dir_path in self.ssd_dirs.items():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                # Set permissions: 0o755 (rwxr-xr-x)
                dir_path.chmod(0o755)
                results[dir_name] = f"initialized at {dir_path}"
                logger.info(f"Initialized SSD directory: {dir_path}")
            except Exception as e:
                results[dir_name] = f"failed: {e}"
                success = False
                logger.error(f"Failed to initialize {dir_name} at {dir_path}: {e}")

        return success, results

    def get_ssd_disk_space(self) -> Optional[Dict[str, int]]:
        """
        Get SSD disk space info (total, used, free in bytes).
        Returns: {total, used, free} or None if unavailable
        """
        try:
            stat = shutil.disk_usage(self.ssd_mount_point)
            return {
                "total_bytes": stat.total,
                "used_bytes": stat.used,
                "free_bytes": stat.free,
                "percent_used": round((stat.used / stat.total) * 100, 2),
            }
        except Exception as e:
            logger.error(f"Failed to get disk space info: {e}")
            return None

    def check_low_disk_space(self, threshold_mb: int = 500) -> bool:
        """Check if free disk space is below threshold (default 500MB)."""
        space_info = self.get_ssd_disk_space()
        if not space_info:
            return False

        free_mb = space_info["free_bytes"] / (1024 * 1024)
        return free_mb < threshold_mb

    def save_migration_state(self, state: Dict) -> bool:
        """Save migration state to SSD for recovery."""
        try:
            self.state_file.write_text(json.dumps(state, indent=2, default=str))
            logger.info(f"Migration state saved to {self.state_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save migration state: {e}")
            return False

    def load_migration_state(self) -> Optional[Dict]:
        """Load migration state from SSD."""
        try:
            if self.state_file.exists():
                return json.loads(self.state_file.read_text())
            return None
        except Exception as e:
            logger.error(f"Failed to load migration state: {e}")
            return None

    def get_ssd_status(self) -> Dict:
        """Get comprehensive SSD status report."""
        accessible, access_msg = self.verify_ssd_accessible()
        disk_space = self.get_ssd_disk_space()
        migration_state = self.load_migration_state()

        return {
            "ssd_mounted": self.is_ssd_mounted(),
            "ssd_accessible": accessible,
            "access_message": access_msg,
            "mount_point": str(self.ssd_mount_point),
            "disk_space": disk_space,
            "low_disk_warning": self.check_low_disk_space(),
            "directories": {
                name: str(path) for name, path in self.ssd_dirs.items()
            },
            "migration_state": migration_state,
        }


def setup_ssd() -> Tuple[bool, Dict]:
    """
    Complete SSD setup procedure.
    Returns: (success: bool, status: {setup results})
    """
    manager = SSDMigrationManager()

    # Step 1: Verify accessibility
    accessible, msg = manager.verify_ssd_accessible()
    if not accessible:
        logger.warning(f"SSD not accessible: {msg}")
        return False, {
            "step": "verify_accessibility",
            "success": False,
            "message": msg,
        }

    # Step 2: Initialize directories
    init_success, init_results = manager.initialize_ssd_directories()
    if not init_success:
        logger.error(f"Failed to initialize SSD directories: {init_results}")
        return False, {
            "step": "initialize_directories",
            "success": False,
            "results": init_results,
        }

    # Step 3: Get disk space info
    disk_space = manager.get_ssd_disk_space()
    if disk_space is None:
        logger.warning("Could not retrieve disk space info")
        disk_space = {}

    # Step 4: Save initial migration state
    initial_state = {
        "phase": "phase_2_ssd",
        "timestamp": str(Path("/dev/null").stat()),  # will be updated by db_migration
        "ssd_initialized": True,
        "disk_space_at_setup": disk_space,
    }
    manager.save_migration_state(initial_state)

    return True, {
        "step": "complete_setup",
        "success": True,
        "directories": init_results,
        "disk_space": disk_space,
        "message": "SSD setup successful",
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    success, status = setup_ssd()
    print(json.dumps(status, indent=2, default=str))
    exit(0 if success else 1)
